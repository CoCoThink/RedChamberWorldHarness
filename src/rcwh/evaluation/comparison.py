"""Anonymous whole-sequence ranking with ties, rejection and two readers."""
import json
import re
from pathlib import Path

from ..candidate_reviews import bound_data, canonical_bytes, digest

DIMENSIONS = ("scene_cohesion", "character_voice", "life_detail", "engineering_feel")


def comparative_reviews(export_root: Path, bindings: list[dict], expected_context: str | None = None) -> dict:
    packet_raw = (export_root / "public/packet.json").read_bytes()
    packet = json.loads(packet_raw)
    mapping = json.loads((export_root / "coordinator/mapping.json").read_bytes())
    if mapping["packet_sha256"] != digest(packet_raw):
        raise ValueError("anonymous packet differs from coordinator record")
    core = {k: v for k, v in mapping.items() if k != "packet_sha256"}
    if packet["coordinator_commitment"] != digest(canonical_bytes(core)):
        raise ValueError("coordinator mapping or author identities changed")
    if expected_context is not None and packet["context_sha256"] != expected_context:
        raise ValueError("comparative packet is stale for current study")
    texts = {}
    for candidate in packet["candidates"]:
        if not isinstance(candidate["token"], str) or candidate["file"] != candidate["token"] + ".txt" or not re.fullmatch(r"read-[a-f0-9]{12}", candidate["token"]):
            raise ValueError("invalid anonymous text path")
        raw = (export_root / "public" / candidate["file"]).read_bytes()
        if digest(raw) != candidate["sha256"]:
            raise ValueError("anonymous candidate text changed")
        if candidate["token"] in texts:
            raise ValueError("duplicate anonymous candidate")
        texts[candidate["token"]] = raw.decode()
    principals, sources, ids = set(), set(), set()
    valid, findings = [], []
    authors = mapping["authors"]
    for binding in bindings:
        try:
            review = bound_data(export_root, binding)
            if review["report_kind"] != "REVIEW_OPINION":
                raise ValueError("reading template is not a submitted comparative opinion")
            reviewer = review["reviewer"]
            if review["packet_sha256"] != digest(packet_raw) or review["context_sha256"] != packet["context_sha256"]:
                raise ValueError("stale comparative review input")
            if reviewer["kind"] != "INDEPENDENT_HUMAN" or any(not isinstance(reviewer[k], str) or not reviewer[k].strip() for k in ("principal_id", "source_id")):
                raise ValueError("comparative review requires identified independent human")
            if not isinstance(review["id"], str) or not review["id"].strip():
                raise ValueError("comparative review requires a nonempty stable review ID")
            if reviewer["mapping_unseen_during_review"] is not True or reviewer["independent_of_authors"] is not True:
                raise ValueError("reader discloses contamination or author dependence")
            if reviewer["principal_id"] in principals or reviewer["source_id"] in sources or review["id"] in ids:
                raise ValueError("duplicate comparative reviewer, source or review")
            if any(reviewer[k] == a[k] for a in authors for k in ("principal_id", "source_id")):
                raise ValueError("comparative reader shares author identity or source")
            ranks = review["ranking"]
            if not isinstance(ranks, list) or any(not isinstance(group, list) for group in ranks):
                raise ValueError("ranking must be a list of token groups")
            flattened = [token for group in ranks for token in group]
            if not ranks or any(not group for group in ranks) or len(flattened) != len(set(flattened)) or set(flattened) != set(texts):
                raise ValueError("ranking must cover all candidates exactly once; groups express ties")
            if review["recommendation"] not in {"CONTINUE", "NEITHER"}:
                raise ValueError("invalid comparative recommendation")
            if set(review["observations"]) != set(texts):
                raise ValueError("incomplete comparative observations")
            for token, dimensions in review["observations"].items():
                if set(dimensions) != set(DIMENSIONS):
                    raise ValueError("incomplete reading dimensions")
                for opinion in dimensions.values():
                    if not opinion["reason"].strip() or not opinion["spans"]:
                        raise ValueError("comparative judgement requires reason and text spans")
                    for span in opinion["spans"]:
                        text = texts[token]
                        if not 0 <= span["start"] < span["end"] <= len(text) or text[span["start"]:span["end"]] != span["quote"]:
                            raise ValueError("invalid comparative text span")
            original = {k: v for k, v in review.items() if k not in {"raw_review", "authority_effect"}}
            if bound_data(export_root, review["raw_review"]) != original:
                raise ValueError("comparative opinion differs from original submission")
            principals.add(reviewer["principal_id"]); sources.add(reviewer["source_id"]); ids.add(review["id"])
            valid.append(original)
        except (KeyError, OSError, TypeError, ValueError) as exc:
            findings.append(str(exc))
    pairwise = []
    tokens = sorted(texts)
    for i, left in enumerate(tokens):
        for right in tokens[i+1:]:
            outcomes = []
            for review in valid:
                positions = {t: j for j, group in enumerate(review["ranking"]) for t in group}
                outcomes.append("TIE" if positions[left] == positions[right] else left if positions[left] < positions[right] else right)
            pairwise.append({"left": left, "right": right, "outcomes": outcomes,
                             "agreement": len(set(outcomes)) == 1 if outcomes else None})
    return {"status": "FAIL" if findings else "PASS" if len(valid) >= 2 else "PENDING", "report_kind": "COMPUTED_CHECK",
            "scope": "COMPARATIVE_READING_ONLY", "review_count": len(valid), "minimum_reviewers": 2,
            "reviews": valid, "pairwise": pairwise, "findings": findings, "automatic_winner": None, "literary_acceptance": "PENDING",
            "independence_basis": "SUBMITTED_IDENTITIES_AND_CUSTODY_ATTESTATIONS", "authority_effect": "NONE"}
