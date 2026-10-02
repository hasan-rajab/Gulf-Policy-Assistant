from pathlib import Path

from app.core.access import AccessContext
from app.services.actions import EnterpriseActionService
from app.services.assurance import run_assurance_review
from app.services.audit import SQLiteAuditStore
from app.services.audit_analytics import analyze_audit_events


def test_four_eyes_control_blocks_admin_self_approval_and_audits_attempt(tmp_path: Path):
    audit = SQLiteAuditStore(tmp_path / "audit.db")
    actions = EnterpriseActionService(tmp_path / "actions.db", audit)
    admin = AccessContext.create("admin@example.com", ["knowledge_admin"], ["governance"])

    requested = actions.request(
        principal=admin,
        action_name="request_policy_exception",
        payload={
            "policy": "Remote Work",
            "exception_reason": "Temporary business need",
            "duration": "1 day",
        },
        request_id="req-1",
        idempotency_key="self-approval-test",
    )

    try:
        actions.approve(requested["id"], admin, "req-2")
        blocked = False
    except PermissionError:
        blocked = True

    assert blocked is True
    denied = [
        event
        for event in audit.list_events()
        if event["action"] == "enterprise_action_approval_attempt"
    ]
    assert denied
    assert denied[-1]["outcome"] == "denied"
    assert denied[-1]["details"]["reason"] == "self_approval_prohibited"


def test_audit_analytics_detects_execution_without_approval_and_self_approval():
    events = [
        {
            "actor": "admin@example.com",
            "action": "enterprise_action_requested",
            "resource": "A-1",
            "outcome": "pending_approval",
            "details": {},
        },
        {
            "actor": "admin@example.com",
            "action": "enterprise_action_approved",
            "resource": "A-1",
            "outcome": "approved",
            "details": {"requester": "admin@example.com"},
        },
        {
            "actor": "operator@example.com",
            "action": "enterprise_action_executed",
            "resource": "A-2",
            "outcome": "executed",
            "details": {},
        },
    ]

    report = analyze_audit_events(events)
    types = {item["type"] for item in report["exceptions"]}

    assert "SELF_APPROVAL" in types
    assert "EXECUTION_WITHOUT_RECORDED_APPROVAL" in types


def test_audit_analytics_flags_repeated_denied_logins():
    events = [
        {
            "actor": "user@example.com",
            "action": "login",
            "resource": None,
            "outcome": "denied",
            "details": {},
        }
        for _ in range(3)
    ]

    report = analyze_audit_events(events, failed_login_threshold=3)

    assert report["exception_count"] == 1
    assert report["exceptions"][0]["type"] == "REPEATED_DENIED_LOGIN"


def test_executable_assurance_review_passes(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    report = run_assurance_review(tmp_path / "review", repo_root=repo_root)

    assert report["control_count"] >= 11
    assert report["failed_count"] == 0
    assert report["overall_passed"] is True
