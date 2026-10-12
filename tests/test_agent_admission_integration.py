"""Research panel reporting never substitutes for existing human qualification."""
from rcwh.acceptance import ProjectAcceptance
from test_project_acceptance import acceptance_inputs


def test_research_panel_is_separate_from_acceptance_checks(acceptance_inputs, monkeypatch):
    root, state, _ = acceptance_inputs
    from rcwh.workflow.agent_panel import AgentPanel
    monkeypatch.setattr(AgentPanel, "summary", lambda *_: {
        "status": "PASS", "independent_human_admission": False})
    result = ProjectAcceptance(root).summary()
    assert result["agent_panel"]["status"] == "PASS"
    assert result["status"] == "PENDING"
    assert result["checks"]["source_independent_reviews"]["status"] == "PENDING"
    assert "agent_panel" not in result["checks"]


def test_agent_rejection_does_not_change_human_acceptance(acceptance_inputs, monkeypatch):
    root, state, _ = acceptance_inputs
    state.update(source_review="PASS", corpus_review="PASS", paired="PASS")
    from rcwh.workflow.agent_panel import AgentPanel
    monkeypatch.setattr(AgentPanel, "summary", lambda *_: {
        "status": "FAIL", "independent_human_admission": False})
    result = ProjectAcceptance(root).summary()
    assert result["status"] == "PASS"
    assert result["agent_panel"]["status"] == "FAIL"
