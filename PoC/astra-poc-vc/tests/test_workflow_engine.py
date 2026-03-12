"""Tests for workflow_engine.py — no external dependencies."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from workflow_engine import WorkflowEngine, WorkflowProposal


def make_engine():
    return WorkflowEngine()


def test_no_proposal_on_first_trigger():
    e = make_engine()
    e.start_turn("email_bloomberg")
    e.log_action("analyze_stock_email_context")
    e.log_action("get_stock_quote")
    e.log_action("emit_ui")
    proposal = e.end_turn()
    # bloomberg seed starts at hit_count=1, so first real hit = 2 = proposal
    assert proposal is not None
    assert proposal.workflow_id == "bloomberg_stock_alert"


def test_proposal_not_repeated():
    e = make_engine()
    # First trigger → proposal
    e.start_turn("email_bloomberg")
    e.log_action("analyze_stock_email_context")
    e.end_turn()
    # Second trigger → no repeat proposal
    e.start_turn("email_bloomberg")
    e.log_action("analyze_stock_email_context")
    proposal2 = e.end_turn()
    assert proposal2 is None, "Should not propose same workflow twice"


def test_enable_disable():
    e = make_engine()
    assert not e.is_enabled("bloomberg_stock_alert")
    e.enable("bloomberg_stock_alert")
    assert e.is_enabled("bloomberg_stock_alert")
    e.disable("bloomberg_stock_alert")
    assert not e.is_enabled("bloomberg_stock_alert")


def test_morning_briefing_always_enabled():
    e = make_engine()
    assert e.is_enabled("morning_briefing")


def test_no_proposal_for_enabled_workflow():
    e = make_engine()
    e.enable("bloomberg_stock_alert")
    e.start_turn("email_bloomberg")
    e.log_action("analyze_stock_email_context")
    proposal = e.end_turn()
    assert proposal is None, "Should not propose already-enabled workflow"


def test_emergent_pattern_detection():
    e = make_engine()
    # Two turns with same trigger + same first 2 actions
    e.start_turn("user_message")
    e.log_action("list_emails")
    e.log_action("emit_ui")
    e.end_turn()

    e.start_turn("user_message")
    e.log_action("list_emails")
    e.log_action("emit_ui")
    proposal = e.end_turn()
    assert proposal is not None, "Should detect emergent pattern"
    assert "list_emails" in proposal.name or "list_emails" in proposal.description


def test_proposal_components_structure():
    e = make_engine()
    e.start_turn("email_bloomberg")
    e.log_action("analyze_stock_email_context")
    proposal = e.end_turn()
    assert proposal is not None
    components = e.to_proposal_components(proposal)
    assert len(components) >= 4
    types = [c["type"] for c in components]
    assert "Card" in types
    assert "Button" in types
    # Enable button should have workflow_enable action
    enable_btn = next(c for c in components if c.get("props", {}).get("label") == "Enable")
    assert "workflow_enable" in enable_btn["props"]["action"]


def test_list_workflows():
    e = make_engine()
    workflows = e.list_workflows()
    assert len(workflows) >= 3
    ids = [w["id"] for w in workflows]
    assert "bloomberg_stock_alert" in ids
    assert "morning_briefing" in ids
    assert "meeting_prep" in ids


if __name__ == "__main__":
    tests = [
        test_no_proposal_on_first_trigger,
        test_proposal_not_repeated,
        test_enable_disable,
        test_morning_briefing_always_enabled,
        test_no_proposal_for_enabled_workflow,
        test_emergent_pattern_detection,
        test_proposal_components_structure,
        test_list_workflows,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
            import traceback; traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{passed+failed} tests passed")
