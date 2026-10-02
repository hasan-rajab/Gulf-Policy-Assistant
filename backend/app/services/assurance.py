from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.core.access import AccessContext
from app.services.actions import EnterpriseActionService
from app.services.audit import SQLiteAuditStore
from app.services.audit_analytics import analyze_audit_events
from app.stores.base import StoredChunk
from app.stores.local import LocalVectorStore


@dataclass(frozen=True)
class ControlTestResult:
    control_id: str
    domain: str
    objective: str
    passed: bool
    evidence: str
    exception: str | None = None


def _capture_blocked(callable_obj, expected: type[BaseException]) -> bool:
    try:
        callable_obj()
    except expected:
        return True
    except Exception:
        return False
    return False


def _result(
    control_id: str,
    domain: str,
    objective: str,
    passed: bool,
    evidence: str,
    exception: str | None = None,
) -> ControlTestResult:
    return ControlTestResult(
        control_id=control_id,
        domain=domain,
        objective=objective,
        passed=bool(passed),
        evidence=evidence,
        exception=exception if not passed else None,
    )


def run_assurance_review(work_dir: Path, repo_root: Path | None = None) -> dict[str, Any]:
    """Execute a deterministic technology-assurance control review.

    The review uses disposable local stores so it can run in CI without cloud
    credentials. It tests the implemented control mechanics; it is not a SOC,
    SOX, ISAE 3402, or external-audit opinion.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    controls: list[ControlTestResult] = []

    audit = SQLiteAuditStore(work_dir / "audit.db")
    actions = EnterpriseActionService(work_dir / "actions.db", audit)
    store = LocalVectorStore(work_dir / "index.json")

    restricted = StoredChunk(
        id="restricted-hr",
        document_id="doc-restricted-hr",
        title="Restricted HR Policy",
        text="restricted compensation policy",
        embedding=[1.0, 0.0],
        chunk_index=0,
        visibility="restricted",
        allowed_departments=["hr"],
    )
    public = StoredChunk(
        id="public-guide",
        document_id="doc-public-guide",
        title="Public Workplace Guide",
        text="general workplace guidance",
        embedding=[0.0, 1.0],
        chunk_index=0,
        visibility="public",
    )
    store.upsert([restricted, public])

    employee = AccessContext.create("employee@example.com", ["employee"], ["operations"])
    hr_user = AccessContext.create("hr@example.com", ["employee"], ["hr"])
    approver = AccessContext.create("approver@example.com", ["knowledge_admin"], ["governance"])
    second_admin = AccessContext.create("second-admin@example.com", ["knowledge_admin"], ["governance"])

    outsider_results = store.search([1.0, 0.0], 5, access=employee)
    controls.append(
        _result(
            "GITC-AC-01",
            "Logical access",
            "Restricted information is excluded before retrieval scoring for unauthorized principals.",
            all(item.chunk.id != "restricted-hr" for item in outsider_results),
            "Disposable LocalVectorStore semantic search executed as operations employee.",
        )
    )

    hr_results = store.search([1.0, 0.0], 5, access=hr_user)
    controls.append(
        _result(
            "GITC-AC-02",
            "Logical access",
            "Authorized department entitlements permit access to the restricted document.",
            bool(hr_results and hr_results[0].chunk.id == "restricted-hr"),
            "Disposable LocalVectorStore semantic search executed as HR principal.",
        )
    )

    requested = actions.request(
        principal=employee,
        action_name="create_it_service_ticket",
        payload={"summary": "VPN access", "description": "Approved remote-work access request"},
        request_id="assurance-request-1",
        idempotency_key="assurance-vpn-1",
    )

    blocked_preapproval = _capture_blocked(
        lambda: actions.execute(requested["id"], approver, "assurance-execute-before-approval"),
        ValueError,
    )
    controls.append(
        _result(
            "ITAC-ACT-01",
            "Application control",
            "Side-effecting action cannot execute before explicit approval.",
            blocked_preapproval,
            "EnterpriseActionService execution attempted from pending_approval state.",
        )
    )

    blocked_non_admin = _capture_blocked(
        lambda: actions.approve(requested["id"], employee, "assurance-non-admin-approval"),
        PermissionError,
    )
    controls.append(
        _result(
            "ITAC-ACT-02",
            "Application control",
            "Only an authorized administrator can approve an action.",
            blocked_non_admin,
            "Approval attempted by employee principal and expected to be denied/audited.",
        )
    )

    admin_request = actions.request(
        principal=approver,
        action_name="request_policy_exception",
        payload={"policy": "Remote Work", "exception_reason": "Testing four-eyes control", "duration": "1 day"},
        request_id="assurance-self-approval-request",
        idempotency_key="assurance-self-approval-1",
    )
    blocked_self_approval = _capture_blocked(
        lambda: actions.approve(admin_request["id"], approver, "assurance-self-approval"),
        PermissionError,
    )
    controls.append(
        _result(
            "ITAC-ACT-03",
            "Segregation of duties",
            "The requester cannot approve their own action, including administrator requesters.",
            blocked_self_approval,
            "Administrator self-approval attempted against four-eyes control.",
        )
    )

    duplicate = actions.request(
        principal=employee,
        action_name="create_it_service_ticket",
        payload={"summary": "VPN access", "description": "Approved remote-work access request"},
        request_id="assurance-request-duplicate",
        idempotency_key="assurance-vpn-1",
    )
    controls.append(
        _result(
            "ITAC-ACT-04",
            "Application control",
            "Idempotency prevents replay from creating a second action request.",
            duplicate["id"] == requested["id"],
            "Repeated request used same requester and idempotency key.",
        )
    )

    blocked_arbitrary_action = _capture_blocked(
        lambda: actions.request(
            principal=employee,
            action_name="run_shell_command",
            payload={"command": "whoami"},
            request_id="assurance-arbitrary-action",
        ),
        ValueError,
    )
    controls.append(
        _result(
            "ITAC-ACT-05",
            "Application control",
            "Only allowlisted, schema-validated enterprise actions can be requested.",
            blocked_arbitrary_action,
            "Unregistered shell-command action name submitted to action service.",
        )
    )

    blocked_idempotency_conflict = _capture_blocked(
        lambda: actions.request(
            principal=employee,
            action_name="create_it_service_ticket",
            payload={"summary": "VPN access", "description": "Changed request under reused key"},
            request_id="assurance-idempotency-conflict",
            idempotency_key="assurance-vpn-1",
        ),
        ValueError,
    )
    controls.append(
        _result(
            "ITAC-ACT-07",
            "Processing integrity",
            "An idempotency key cannot be reused for a materially different request.",
            blocked_idempotency_conflict,
            "Reused the original idempotency key with a changed payload.",
        )
    )

    blocked_nonfinite_input = _capture_blocked(
        lambda: actions.request(
            principal=employee,
            action_name="create_it_service_ticket",
            payload={"summary": "Capacity", "description": "Numeric edge case", "priority": float("nan")},
            request_id="assurance-nonfinite-input",
        ),
        ValueError,
    )
    controls.append(
        _result(
            "ITAC-ACT-08",
            "Input validation",
            "Malformed non-finite numeric values are rejected before persistence.",
            blocked_nonfinite_input,
            "Submitted a NaN priority value through the action payload validator.",
        )
    )

    actions.approve(admin_request["id"], second_admin, "assurance-admin-request-approval")
    blocked_requester_execution = _capture_blocked(
        lambda: actions.execute(admin_request["id"], approver, "assurance-requester-execution"),
        PermissionError,
    )
    controls.append(
        _result(
            "ITAC-ACT-09",
            "Segregation of duties",
            "A privileged requester cannot execute their own request after independent approval.",
            blocked_requester_execution,
            "Administrator requester attempted execution after approval by a second administrator.",
        )
    )

    approved = actions.approve(requested["id"], approver, "assurance-approval")
    executed = actions.execute(requested["id"], second_admin, "assurance-execution")
    controls.append(
        _result(
            "ITAC-ACT-06",
            "Application control",
            "Approved action follows the persisted pending -> approved -> executed workflow.",
            approved["status"] == "approved" and executed["status"] == "executed",
            "Normal action lifecycle executed with distinct requester and approver.",
        )
    )

    chain_valid = audit.verify_chain()
    controls.append(
        _result(
            "GITC-OPS-01",
            "IT operations / logging",
            "Audit records remain internally consistent under the hash chain.",
            chain_valid,
            "SQLiteAuditStore.verify_chain() executed after control-test activity.",
        )
    )

    analytics = analyze_audit_events(audit.list_events())
    controls.append(
        _result(
            "GITC-MON-01",
            "Monitoring",
            "Deterministic audit analytics identify no execution-without-approval or self-approval exceptions in the valid workflow.",
            analytics["exception_count"] == 0,
            f"Analyzed {analytics['event_count']} structured audit events.",
            None if analytics["exception_count"] == 0 else str(analytics["exceptions"]),
        )
    )

    tamper_audit = SQLiteAuditStore(work_dir / "tamper-audit.db")
    tamper_audit.record(
        actor="employee@example.com",
        action="rag_query",
        resource="conversation-1",
        outcome="grounded",
        request_id="assurance-tamper-1",
        details={"source_count": 1},
    )
    tamper_audit._connection.execute(
        "UPDATE audit_events SET outcome='tampered' WHERE sequence=1"
    )
    tamper_audit._connection.commit()
    controls.append(
        _result(
            "GITC-OPS-02",
            "IT operations / logging",
            "Stored audit-event modification is detectable by hash-chain verification.",
            tamper_audit.verify_chain() is False,
            "Controlled database tampering performed against disposable audit store.",
        )
    )

    truncation_audit = SQLiteAuditStore(work_dir / "truncation-audit.db")
    first_event = truncation_audit.record(
        actor="employee@example.com",
        action="rag_query",
        resource="conversation-a",
        outcome="grounded",
        request_id="assurance-truncation-1",
        details={},
    )
    truncation_audit.record(
        actor="employee@example.com",
        action="rag_query",
        resource="conversation-b",
        outcome="grounded",
        request_id="assurance-truncation-2",
        details={},
    )
    truncation_audit._connection.execute(
        "DELETE FROM audit_events WHERE event_id != ?",
        (first_event["event_id"],),
    )
    truncation_audit._connection.commit()
    controls.append(
        _result(
            "GITC-OPS-03",
            "IT operations / logging",
            "Deletion of the most recent audit event is detectable against the persisted chain checkpoint.",
            truncation_audit.verify_chain() is False,
            "Deleted the tail event from a disposable two-event audit chain.",
        )
    )

    required_field_audit = SQLiteAuditStore(work_dir / "required-field-audit.db")
    blocked_blank_audit_field = _capture_blocked(
        lambda: required_field_audit.record(
            actor="",
            action="rag_query",
            resource=None,
            outcome="grounded",
            request_id="assurance-required-fields",
            details={},
        ),
        ValueError,
    )
    controls.append(
        _result(
            "GITC-OPS-04",
            "IT operations / logging",
            "Required audit identity/action/outcome fields cannot be blank.",
            blocked_blank_audit_field,
            "Attempted to persist an audit event with a blank actor.",
        )
    )

    provenance_audit = SQLiteAuditStore(work_dir / "provenance-audit.db")
    provenance_actions = EnterpriseActionService(work_dir / "provenance-actions.db", provenance_audit)
    provenance_request = provenance_actions.request(
        principal=employee,
        action_name="create_it_service_ticket",
        payload={"summary": "VPN access", "description": "Approval provenance test"},
        request_id="assurance-provenance-request",
        idempotency_key="assurance-provenance-1",
    )
    provenance_actions._connection.execute(
        "UPDATE action_requests SET status='approved' WHERE id=?",
        (provenance_request["id"],),
    )
    provenance_actions._connection.commit()
    blocked_forged_approval = _capture_blocked(
        lambda: provenance_actions.execute(
            provenance_request["id"], second_admin, "assurance-provenance-execute"
        ),
        ValueError,
    )
    controls.append(
        _result(
            "ITAC-ACT-10",
            "Authorization / processing integrity",
            "Execution requires complete, independent approval provenance rather than status alone.",
            blocked_forged_approval,
            "Directly flipped a disposable action row to approved without approver metadata.",
        )
    )

    synthetic_exceptions = analyze_audit_events(
        [
            {
                "actor": "requester@example.com",
                "action": "enterprise_action_requested",
                "resource": "SYN-1",
                "outcome": "pending_approval",
                "details": {},
            },
            {
                "actor": "requester@example.com",
                "action": "enterprise_action_approved",
                "resource": "SYN-1",
                "outcome": "approved",
                "details": {"requester": "requester@example.com"},
            },
            {
                "actor": "requester@example.com",
                "action": "enterprise_action_executed",
                "resource": "SYN-1",
                "outcome": "executed",
                "details": {},
            },
            {
                "actor": "admin@example.com",
                "action": "enterprise_action_executed",
                "resource": "UNKNOWN",
                "outcome": "executed",
                "details": {},
            },
        ]
    )
    synthetic_types = {item["type"] for item in synthetic_exceptions["exceptions"]}
    expected_types = {
        "SELF_APPROVAL",
        "REQUESTER_EXECUTION",
        "EXECUTION_WITHOUT_REQUEST",
        "EXECUTION_WITHOUT_RECORDED_APPROVAL",
    }
    controls.append(
        _result(
            "GITC-MON-02",
            "Monitoring",
            "Exception analytics surface deliberately injected approval/execution violations.",
            expected_types.issubset(synthetic_types),
            "Analyzed a synthetic event sequence containing known control violations.",
            None if expected_types.issubset(synthetic_types) else str(sorted(synthetic_types)),
        )
    )

    if repo_root is not None:
        workflow_path = repo_root / ".github" / "workflows" / "ci.yml"
        workflow = workflow_path.read_text(encoding="utf-8") if workflow_path.exists() else ""
        required_ci_evidence = (
            "pytest -q backend/tests",
            "backend/scripts/evaluate.py",
            "npm run build",
            "docker compose config --quiet",
        )
        ci_pass = all(item in workflow for item in required_ci_evidence)
        controls.append(
            _result(
                "GITC-CM-01",
                "Change management",
                "Repository changes are subject to automated backend/security, AI-evaluation, frontend-build, and deployment-configuration checks.",
                ci_pass,
                ".github/workflows/ci.yml inspected for required quality gates.",
                None if ci_pass else "One or more required CI quality gates are absent.",
            )
        )

        eval_path = repo_root / "evaluation" / "eval_set.json"
        if eval_path.exists():
            import json

            cases = json.loads(eval_path.read_text(encoding="utf-8"))
            languages = {str(case.get("language") or "").lower() for case in cases}
            grounded_values = {bool(case.get("expect_grounded", True)) for case in cases}
            case_text = " ".join(str(case).lower() for case in cases)
            coverage_ok = (
                len(cases) >= 8
                and {"en", "ar"}.issubset(languages)
                and grounded_values == {True, False}
                and ("ignore" in case_text or "injection" in case_text)
            )
        else:
            coverage_ok = False
        controls.append(
            _result(
                "AI-ASSUR-01",
                "AI assurance",
                "The regression design covers bilingual behavior, grounded/abstaining decisions, and an adversarial instruction case.",
                coverage_ok,
                "evaluation/eval_set.json inspected for minimum controlled assurance coverage.",
                None if coverage_ok else "Evaluation-set assurance coverage is incomplete.",
            )
        )

    failed = [asdict(item) for item in controls if not item.passed]
    return {
        "review_name": "NEXUS Technology Assurance Control Review",
        "scope": "deterministic local control mechanics and repository quality gates",
        "control_count": len(controls),
        "passed_count": len(controls) - len(failed),
        "failed_count": len(failed),
        "overall_passed": not failed,
        "controls": [asdict(item) for item in controls],
        "audit_analytics": analytics,
        "claims_boundary": (
            "This is repository-backed control testing on a fictional demo system. "
            "It is not a SOC report, SOX opinion, ISAE 3402 engagement, certification, "
            "or evidence of production operating effectiveness over a real client population."
        ),
    }
