from __future__ import annotations

import math
from pathlib import Path

import pytest

from app.core.access import AccessContext
from app.services.actions import EnterpriseActionService
from app.services.audit import SQLiteAuditStore
from app.services.audit_analytics import analyze_audit_events


@pytest.fixture
def action_env(tmp_path: Path):
    audit = SQLiteAuditStore(tmp_path / "audit.db")
    actions = EnterpriseActionService(tmp_path / "actions.db", audit)
    employee = AccessContext.create("employee@example.com", ["employee"], ["operations"])
    admin_a = AccessContext.create("admin-a@example.com", ["knowledge_admin"], ["governance"])
    admin_b = AccessContext.create("admin-b@example.com", ["knowledge_admin"], ["governance"])
    return audit, actions, employee, admin_a, admin_b


def _ticket_payload(description: str = "Approved remote-work access request"):
    return {"summary": "VPN access", "description": description}


def test_idempotency_key_reuse_with_changed_payload_is_rejected_and_audited(action_env):
    audit, actions, employee, _, _ = action_env
    actions.request(
        principal=employee,
        action_name="create_it_service_ticket",
        payload=_ticket_payload("Original request"),
        request_id="req-1",
        idempotency_key="idem-1",
    )

    with pytest.raises(ValueError, match="Idempotency key conflict"):
        actions.request(
            principal=employee,
            action_name="create_it_service_ticket",
            payload=_ticket_payload("Changed request"),
            request_id="req-2",
            idempotency_key="idem-1",
        )

    assert any(
        event["action"] == "enterprise_action_request_rejected"
        and event["details"].get("reason") == "idempotency_key_conflict"
        for event in audit.list_events()
    )


def test_idempotency_key_reuse_for_different_action_is_rejected(action_env):
    _, actions, employee, _, _ = action_env
    actions.request(
        principal=employee,
        action_name="create_it_service_ticket",
        payload=_ticket_payload(),
        request_id="req-1",
        idempotency_key="idem-2",
    )

    with pytest.raises(ValueError, match="Idempotency key conflict"):
        actions.request(
            principal=employee,
            action_name="request_hr_policy_review",
            payload={"policy_question": "Leave", "business_reason": "Planning"},
            request_id="req-2",
            idempotency_key="idem-2",
        )


def test_privileged_requester_cannot_execute_own_action_after_independent_approval(action_env):
    audit, actions, _, admin_a, admin_b = action_env
    requested = actions.request(
        principal=admin_a,
        action_name="request_policy_exception",
        payload={
            "policy": "Remote Work",
            "exception_reason": "Temporary operational requirement",
            "duration": "1 day",
        },
        request_id="req-1",
        idempotency_key="sod-exec-1",
    )
    actions.approve(requested["id"], admin_b, "req-2")

    with pytest.raises(PermissionError, match="Requester cannot execute"):
        actions.execute(requested["id"], admin_a, "req-3")

    assert any(
        event["action"] == "enterprise_action_execution_attempt"
        and event["details"].get("reason") == "requester_execution_prohibited"
        for event in audit.list_events()
    )


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_numeric_payload_values_are_rejected(action_env, bad_value):
    _, actions, employee, _, _ = action_env
    with pytest.raises(ValueError, match="finite"):
        actions.request(
            principal=employee,
            action_name="create_it_service_ticket",
            payload={
                "summary": "Capacity",
                "description": "Numeric validation test",
                "priority": bad_value,
            },
            request_id="req-1",
        )


def test_blank_idempotency_key_is_rejected(action_env):
    _, actions, employee, _, _ = action_env
    with pytest.raises(ValueError, match="Idempotency key cannot be blank"):
        actions.request(
            principal=employee,
            action_name="create_it_service_ticket",
            payload=_ticket_payload(),
            request_id="req-1",
            idempotency_key="   ",
        )


def test_audit_analytics_flags_approval_without_request():
    report = analyze_audit_events(
        [
            {
                "actor": "admin@example.com",
                "action": "enterprise_action_approved",
                "resource": "A-1",
                "outcome": "approved",
                "details": {"requester": "employee@example.com"},
            }
        ]
    )
    assert "APPROVAL_WITHOUT_REQUEST" in {item["type"] for item in report["exceptions"]}


def test_audit_analytics_flags_duplicate_approval():
    events = [
        {
            "actor": "employee@example.com",
            "action": "enterprise_action_requested",
            "resource": "A-1",
            "outcome": "pending_approval",
            "details": {},
        },
        {
            "actor": "admin-a@example.com",
            "action": "enterprise_action_approved",
            "resource": "A-1",
            "outcome": "approved",
            "details": {"requester": "employee@example.com"},
        },
        {
            "actor": "admin-b@example.com",
            "action": "enterprise_action_approved",
            "resource": "A-1",
            "outcome": "approved",
            "details": {"requester": "employee@example.com"},
        },
    ]
    report = analyze_audit_events(events)
    assert "DUPLICATE_APPROVAL" in {item["type"] for item in report["exceptions"]}


def test_audit_analytics_flags_duplicate_execution():
    events = [
        {
            "actor": "employee@example.com",
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
            "details": {"requester": "employee@example.com"},
        },
        {
            "actor": "admin@example.com",
            "action": "enterprise_action_executed",
            "resource": "A-1",
            "outcome": "executed",
            "details": {},
        },
        {
            "actor": "admin@example.com",
            "action": "enterprise_action_executed",
            "resource": "A-1",
            "outcome": "executed",
            "details": {},
        },
    ]
    report = analyze_audit_events(events)
    assert "DUPLICATE_EXECUTION" in {item["type"] for item in report["exceptions"]}


def test_audit_analytics_flags_requester_execution():
    events = [
        {
            "actor": "admin-a@example.com",
            "action": "enterprise_action_requested",
            "resource": "A-1",
            "outcome": "pending_approval",
            "details": {},
        },
        {
            "actor": "admin-b@example.com",
            "action": "enterprise_action_approved",
            "resource": "A-1",
            "outcome": "approved",
            "details": {"requester": "admin-a@example.com"},
        },
        {
            "actor": "admin-a@example.com",
            "action": "enterprise_action_executed",
            "resource": "A-1",
            "outcome": "executed",
            "details": {},
        },
    ]
    report = analyze_audit_events(events)
    assert "REQUESTER_EXECUTION" in {item["type"] for item in report["exceptions"]}


def test_audit_analytics_flags_execution_for_unknown_resource():
    report = analyze_audit_events(
        [
            {
                "actor": "admin@example.com",
                "action": "enterprise_action_executed",
                "resource": "UNKNOWN",
                "outcome": "executed",
                "details": {},
            }
        ]
    )
    types = {item["type"] for item in report["exceptions"]}
    assert "EXECUTION_WITHOUT_REQUEST" in types
    assert "EXECUTION_WITHOUT_RECORDED_APPROVAL" in types



def test_audit_chain_detects_tail_event_deletion(tmp_path: Path):
    audit = SQLiteAuditStore(tmp_path / "audit-tail.db")
    first = audit.record(
        actor="employee@example.com",
        action="rag_query",
        resource="conversation-1",
        outcome="grounded",
        request_id="req-1",
        details={"source_count": 1},
    )
    audit.record(
        actor="employee@example.com",
        action="rag_query",
        resource="conversation-2",
        outcome="grounded",
        request_id="req-2",
        details={"source_count": 2},
    )
    assert audit.verify_chain() is True

    audit._connection.execute(
        "DELETE FROM audit_events WHERE event_id != ?",
        (first["event_id"],),
    )
    audit._connection.commit()

    assert audit.verify_chain() is False


def test_execution_rejects_database_status_flip_without_approval_metadata(action_env):
    audit, actions, employee, _, admin_b = action_env
    requested = actions.request(
        principal=employee,
        action_name="create_it_service_ticket",
        payload=_ticket_payload(),
        request_id="req-1",
        idempotency_key="tamper-status-1",
    )

    actions._connection.execute(
        "UPDATE action_requests SET status='approved' WHERE id=?",
        (requested["id"],),
    )
    actions._connection.commit()

    with pytest.raises(ValueError, match="approval metadata"):
        actions.execute(requested["id"], admin_b, "req-2")

    assert any(
        event["action"] == "enterprise_action_execution_attempt"
        and event["details"].get("reason") == "invalid_approval_metadata"
        for event in audit.list_events()
    )


def test_execution_rejects_tampered_self_approval_metadata(action_env):
    audit, actions, _, admin_a, admin_b = action_env
    requested = actions.request(
        principal=admin_a,
        action_name="request_policy_exception",
        payload={
            "policy": "Remote Work",
            "exception_reason": "Test forged approval provenance",
            "duration": "1 day",
        },
        request_id="req-1",
        idempotency_key="tamper-approval-1",
    )

    actions._connection.execute(
        """
        UPDATE action_requests
        SET status='approved', approved_at=?, approved_by=?
        WHERE id=?
        """,
        ("2026-10-02T18:00:00+00:00", admin_a.email, requested["id"]),
    )
    actions._connection.commit()

    with pytest.raises(ValueError, match="approval metadata"):
        actions.execute(requested["id"], admin_b, "req-2")

    assert any(
        event["action"] == "enterprise_action_execution_attempt"
        and event["details"].get("reason") == "invalid_approval_metadata"
        for event in audit.list_events()
    )


@pytest.mark.parametrize(
    "actor,action,outcome",
    [
        ("", "rag_query", "grounded"),
        ("employee@example.com", "", "grounded"),
        ("employee@example.com", "rag_query", ""),
    ],
)
def test_audit_store_rejects_blank_required_event_fields(tmp_path: Path, actor: str, action: str, outcome: str):
    audit = SQLiteAuditStore(tmp_path / "audit-required-fields.db")
    with pytest.raises(ValueError, match="must be non-empty"):
        audit.record(
            actor=actor,
            action=action,
            resource=None,
            outcome=outcome,
            request_id="req-1",
            details={},
        )
