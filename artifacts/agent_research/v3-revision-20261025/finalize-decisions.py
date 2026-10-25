"""Bind explicit coordinator rulings after actual reading; creates no peer opinions."""
from collections import defaultdict
import json
from pathlib import Path

from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.records import binding, bound_bytes
from rcwh.workflow.agent_release import AgentRelease
from rcwh.workflow.release_packets import _write_immutable
from rcwh.workflow.review_campaign import status

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/agent_research/review-campaign-20261021"
CURRENT = ROOT / "artifacts/agent_research/v3-revision-20261025"
REQUEST = "data/agent_release/research-81-100-v3/request.json"
PLAN = "data/agent_release/research-81-100-v3/review-campaign-v1.json"


def main():
    campaign = status(ROOT, PLAN)
    if len(campaign["jobs"]) != 76 or any(j["status"] != "COMPLETE" or j["needs_followup"] for j in campaign["jobs"]):
        raise ValueError("all 76 current jobs must be complete without follow-up")
    known = {}
    results = {}
    for directory, expected in ((ROOT / "artifacts/agent_research/review-campaign-20261021", 76),
                                (ROOT / "artifacts/agent_research/review-campaign-20261021/rereview-v2", 46),
                                (CURRENT, None)):
        registrations = sorted(directory.glob("registration-*.json"))
        if (expected is not None and len(registrations) != expected) or not registrations:
            raise ValueError("unexpected actual registration count")
        read = {r["record"]["sha256"] for r in map(json.loads, (directory / "coordinator-notes-read.jsonl").read_text().splitlines())
                if r["scope"] == "ALL_RESULT_NOTES_AND_SAMPLE_CHECKS_READ_BY_COORDINATOR" and r["peer_credit"] is False}
        for path in registrations:
            registration = json.loads(path.read_bytes())
            ref = registration["record"]
            if ref["sha256"] not in read:
                raise ValueError(f"coordinator reading not recorded: {ref['sha256']}")
            opinion = json.loads(bound_bytes(ROOT, ref))["opinion"]
            known[ref["sha256"]] = ref
            for result in opinion["results"]:
                results[(ref["sha256"], result["subject_id"])] = result
    for job in campaign["jobs"]:
        if job["record"] is None or known.get(job["record"]["sha256"]) != job["record"]:
            raise ValueError("current job record not retained/read")
    ledger_ref = binding(ROOT, str((CURRENT / "coordinator-dispositions.json").relative_to(ROOT)))
    ledger = json.loads(bound_bytes(ROOT, ledger_ref))
    if ledger["status"] != "FINAL_ROOT_COORDINATOR_RULINGS" or ledger["authority_effect"] != "NONE":
        raise ValueError("explicit final coordinator rulings required")
    comparison_ref = binding(ROOT, str((CURRENT / "comparison/summary.json").relative_to(ROOT)))
    comparison = json.loads(bound_bytes(ROOT, comparison_ref))
    changed = json.loads((CURRENT / "design-decisions.json").read_bytes())["changed_chapters"]
    if (comparison["status"] != "COMPLETE_MODEL_COMPARISON_NOT_LITERARY_PASS"
            or comparison["P9_credit"] is not False
            or set(comparison["votes"]) != {str(ch) for ch in changed}
            or any(sum(v.values()) != 2 for v in comparison["votes"].values())
            or ledger["comparison"] != comparison_ref):
        raise ValueError("actual complete model comparison required; no P9 credit")
    assistance = binding(ROOT, str((CURRENT / "design-assistance-ledger.json").relative_to(ROOT)))
    if ledger["editorial_assistance"] != assistance:
        raise ValueError("editorial assistance disclosure omitted")
    issues = {(i["record"]["sha256"], i["subject_id"]): i for i in ledger["issues"]}
    negative = {key for key, result in results.items() if result["verdict"] in {"FAIL", "REJECT"}}
    if not negative <= issues.keys():
        raise ValueError("ledger omitted a negative result")
    for key, issue in issues.items():
        if issue["original_result"] != results[key] or not issue["rationale"].strip():
            raise ValueError("ledger changed original result or omitted its specific ruling")

    runtime = AgentRelease(ROOT)
    report = runtime.evaluate(REQUEST)
    if report["status"] == "FAIL" or report["findings"]:
        raise ValueError("a coordinator decision cannot lift current blocking findings")
    if any(value != "PASS" for c in report["chapters"] for name, value in c["gates"].items() if name != "COORDINATOR_DECISION"):
        raise ValueError("non-coordinator gates must independently pass first")
    request = json.loads((ROOT / REQUEST).read_bytes())
    _write_immutable(ROOT, str((CURRENT / "request-before-decisions.json").relative_to(ROOT)), request)
    reports = {c["chapter"]: c for c in report["chapters"]}
    decisions = []
    for row in request["chapters"]:
        chapter = row["chapter"]
        ruling = ledger["chapters"][str(chapter)]
        if ruling["outcome"] not in {"ADOPT", "REJECT", "PENDING", "TIE", "NEUTRAL"}:
            raise ValueError("explicit chapter outcome required")
        reviews = reports[chapter]["reviews"]
        subjects = [reviews["candidate"]] + [s for k in ("contract_reviews", "source_reviews", "corpus_reviews") for s in reviews.get(k, [])]
        opinions = {}
        dissent = defaultdict(dict)
        for subject in subjects:
            for key in ("opinions", "prior_context_opinions"):
                for opinion in subject.get(key, []):
                    ref = opinion["record"]
                    if known.get(ref["sha256"]) != ref:
                        raise ValueError("unread or unknown contextual opinion")
                    opinions[ref["sha256"]] = ref
                    if opinion["verdict"] in {"FAIL", "REJECT"}:
                        issue_key = (ref["sha256"], opinion["subject_id"])
                        issue = issues[issue_key]
                        if issue["original_result"].get("severity") != "ADVISORY":
                            raise ValueError("cannot overrule a blocking opinion")
                        dissent[ref["sha256"]][opinion["subject_id"]] = issue["rationale"]
        packet = json.loads(bound_bytes(ROOT, row["panel"]["packet"]))
        decision = {"schema_version": 1, "decision_kind": "AGENT_RELEASE_COORDINATOR_DECISION",
                    "chapter": chapter, "candidate": row["candidate"], "outcome": ruling["outcome"],
                    "coordinator_session_id": packet["coordinator_session_id"],
                    "rationale": ruling["rationale"] + f" 完整逐项处置台账：{ledger_ref['path']}（SHA256 {ledger_ref['sha256']}）；这是研究轨采用，不是消除所有ADVISORY或取得人工资格。",
                    "considered_opinions": [opinions[k] for k in sorted(opinions)],
                    "rejected_opinions": [{"record": opinions[k], "rationale": "；".join(f"{s}：{reason}" for s, reason in sorted(v.items()))}
                                          for k, v in sorted(dissent.items())], "authority_effect": "NONE"}
        runtime._validate(decision, "decision")
        ref = _write_immutable(ROOT, f"data/agent_release/research-81-100-v3/coordinator/ch{chapter}.json", decision)
        row["decision"] = ref
        decisions.append({"chapter": chapter, "outcome": ruling["outcome"], "decision": ref,
                          "considered_records": len(opinions), "retained_dissent_records": len(dissent)})
    runtime._validate(request, "request")
    (ROOT / REQUEST).write_bytes(canonical_bytes(request))
    # Adding decisions must not change any frozen reader input or campaign basis.
    after = status(ROOT, PLAN)
    if any(j["status"] != "COMPLETE" for j in after["jobs"]):
        raise ValueError("decision binding changed campaign completion")
    result = {"status": "PASS", "scope": "EXPLICIT_COORDINATOR_DECISION_BINDING",
              "ledger": ledger_ref, "decisions": decisions, "request": binding(ROOT, REQUEST),
              "authority_effect": "NONE", "release_evaluation": "REQUIRED_SEPARATELY"}
    _write_immutable(ROOT, str((CURRENT / "coordinator-decision-bindings.json").relative_to(ROOT)), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
