from __future__ import annotations

import argparse
import json
import math
import tempfile
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.core.access import AccessContext
from app.services.actions import EnterpriseActionService
from app.services.audit import SQLiteAuditStore
from app.services.audit_analytics import analyze_audit_events
from app.stores.base import StoredChunk
from app.stores.local import LocalVectorStore


DANGEROUS_TEXTS = [
    "normal\u202ereversed",
    "normal\u202dforced-ltr",
    "normal\u2066isolate",
    "normal\u2067rtl-isolate",
    "normal\u2068first-strong",
    "normal\u2069pop-isolate",
    "normal\x00nul",
    "normal\x01soh",
    "normal\x1funit-separator",
    "normal\u200bzero-width-space",
]


@dataclass
class CampaignCase:
    case_id: int
    difficulty_score: int
    tier: int
    family: str
    passed: bool
    expected: str
    observed: str
    finding_key: str | None = None


def _blocked(fn, exc_type: type[BaseException]) -> tuple[bool, str]:
    try:
        fn()
    except exc_type as exc:
        return True, f"blocked:{type(exc).__name__}:{exc}"
    except Exception as exc:
        return False, f"wrong_exception:{type(exc).__name__}:{exc}"
    return False, "not_blocked"


def _benign_noise(count: int) -> list[dict[str, Any]]:
    # Each later case contains strictly more unrelated event noise than the
    # previous case. The campaign therefore has a monotonically increasing
    # difficulty score even though the primary control family rotates.
    return [
        {
            "actor": f"noise-{idx % 17}@example.com",
            "action": "health_check",
            "resource": f"noise-{idx}",
            "outcome": "success",
            "details": {"sequence": idx},
        }
        for idx in range(count)
    ]


def _clean_noise_check(difficulty: int) -> tuple[bool, str]:
    report = analyze_audit_events(_benign_noise(difficulty))
    ok = report["exception_count"] == 0
    return ok, f"noise_events={difficulty}, exceptions={report['exception_count']}"


def _acl_case(root: Path, case_id: int, difficulty: int) -> tuple[bool, str]:
    store = LocalVectorStore(root / f"acl-{case_id}.json")
    restricted = StoredChunk(
        id=f"restricted-{case_id}",
        document_id=f"restricted-doc-{case_id}",
        title="Restricted Compensation",
        text="confidential compensation policy",
        embedding=[1.0, 0.0],
        chunk_index=0,
        visibility="restricted",
        allowed_departments=["hr"],
    )
    # Cap persisted distractors while difficulty continues to grow through the
    # campaign-wide event-noise check.
    distractor_count = min(difficulty, 80)
    distractors = [
        StoredChunk(
            id=f"public-{case_id}-{idx}",
            document_id=f"public-doc-{case_id}-{idx}",
            title=f"Public guide {idx}",
            text="general workplace guidance",
            embedding=[0.0, 1.0],
            chunk_index=0,
            visibility="public",
        )
        for idx in range(distractor_count)
    ]
    store.upsert([restricted, *distractors])
    outsider = AccessContext.create(
        f"ops-{case_id}@example.com",
        roles=["employee"],
        departments=["operations"],
    )
    semantic = store.search([1.0, 0.0], 10, access=outsider)
    lexical = store.hybrid_search(
        "confidential compensation policy",
        [1.0, 0.0],
        10,
        access=outsider,
    )
    leaked = any(x.chunk.id == restricted.id for x in [*semantic, *lexical])
    return (not leaked), f"distractors={distractor_count}, restricted_leaked={leaked}"


def _service(root: Path, case_id: int):
    audit = SQLiteAuditStore(root / f"audit-{case_id}.db")
    actions = EnterpriseActionService(root / f"actions-{case_id}.db", audit)
    employee = AccessContext.create(
        f"employee-{case_id}@example.com", ["employee"], ["operations"]
    )
    admin_a = AccessContext.create(
        f"admin-a-{case_id}@example.com", ["knowledge_admin"], ["governance"]
    )
    admin_b = AccessContext.create(
        f"admin-b-{case_id}@example.com", ["knowledge_admin"], ["governance"]
    )
    return audit, actions, employee, admin_a, admin_b


def _idempotency_case(root: Path, case_id: int, difficulty: int) -> tuple[bool, str]:
    audit, actions, employee, _, _ = _service(root, case_id)
    key = f"idem-{case_id}"
    original = "A" * min(10 + difficulty, 500)
    changed = original + "-changed"
    actions.request(
        principal=employee,
        action_name="create_it_service_ticket",
        payload={"summary": "VPN access", "description": original},
        request_id=f"r-{case_id}-1",
        idempotency_key=key,
    )
    blocked, observed = _blocked(
        lambda: actions.request(
            principal=employee,
            action_name="create_it_service_ticket",
            payload={"summary": "VPN access", "description": changed},
            request_id=f"r-{case_id}-2",
            idempotency_key=key,
        ),
        ValueError,
    )
    audited = any(
        e["action"] == "enterprise_action_request_rejected"
        and e["details"].get("reason") == "idempotency_key_conflict"
        for e in audit.list_events()
    )
    return blocked and audited, f"{observed}, denial_audited={audited}"


def _self_approval_case(root: Path, case_id: int, difficulty: int) -> tuple[bool, str]:
    audit, actions, _, admin_a, _ = _service(root, case_id)
    requested = actions.request(
        principal=admin_a,
        action_name="request_policy_exception",
        payload={
            "policy": "Remote Work",
            "exception_reason": "X" * min(20 + difficulty, 600),
            "duration": "1 day",
        },
        request_id=f"r-{case_id}-1",
        idempotency_key=f"sod-{case_id}",
    )
    blocked, observed = _blocked(
        lambda: actions.approve(requested["id"], admin_a, f"r-{case_id}-2"),
        PermissionError,
    )
    audited = any(
        e["action"] == "enterprise_action_approval_attempt"
        and e["details"].get("reason") == "self_approval_prohibited"
        for e in audit.list_events()
    )
    return blocked and audited, f"{observed}, denial_audited={audited}"


def _requester_execution_case(root: Path, case_id: int, difficulty: int) -> tuple[bool, str]:
    audit, actions, _, admin_a, admin_b = _service(root, case_id)
    requested = actions.request(
        principal=admin_a,
        action_name="request_policy_exception",
        payload={
            "policy": "Remote Work",
            "exception_reason": "Y" * min(20 + difficulty, 600),
            "duration": "1 day",
        },
        request_id=f"r-{case_id}-1",
        idempotency_key=f"exec-sod-{case_id}",
    )
    actions.approve(requested["id"], admin_b, f"r-{case_id}-2")
    blocked, observed = _blocked(
        lambda: actions.execute(requested["id"], admin_a, f"r-{case_id}-3"),
        PermissionError,
    )
    audited = any(
        e["action"] == "enterprise_action_execution_attempt"
        and e["details"].get("reason") == "requester_execution_prohibited"
        for e in audit.list_events()
    )
    return blocked and audited, f"{observed}, denial_audited={audited}"


def _analytics_case(case_id: int, difficulty: int, kind: str) -> tuple[bool, str]:
    events = _benign_noise(difficulty)
    resource = f"A-{case_id}"
    if kind == "orphan_execution":
        events.append(
            {
                "actor": "admin@example.com",
                "action": "enterprise_action_executed",
                "resource": resource,
                "outcome": "executed",
                "details": {},
            }
        )
        required = {"EXECUTION_WITHOUT_REQUEST", "EXECUTION_WITHOUT_RECORDED_APPROVAL"}
    else:
        events.extend(
            [
                {
                    "actor": "employee@example.com",
                    "action": "enterprise_action_requested",
                    "resource": resource,
                    "outcome": "pending_approval",
                    "details": {},
                },
                {
                    "actor": "admin-a@example.com",
                    "action": "enterprise_action_approved",
                    "resource": resource,
                    "outcome": "approved",
                    "details": {"requester": "employee@example.com"},
                },
                {
                    "actor": "admin-b@example.com",
                    "action": "enterprise_action_approved",
                    "resource": resource,
                    "outcome": "approved",
                    "details": {"requester": "employee@example.com"},
                },
            ]
        )
        required = {"DUPLICATE_APPROVAL"}
    report = analyze_audit_events(events)
    types = {x["type"] for x in report["exceptions"]}
    ok = required.issubset(types)
    return ok, f"events={len(events)}, detected={sorted(types)}"


def _audit_tamper_case(root: Path, case_id: int, difficulty: int) -> tuple[bool, str]:
    audit = SQLiteAuditStore(root / f"tamper-{case_id}.db")
    event_count = 3 + (difficulty % 5)
    for idx in range(event_count):
        audit.record(
            actor="employee@example.com",
            action="rag_query",
            resource=f"conversation-{idx}",
            outcome="grounded",
            request_id=f"r-{case_id}-{idx}",
            details={"source_count": idx + 1},
        )
    mutation = case_id % 4
    if mutation == 0:
        audit._connection.execute(
            "UPDATE audit_events SET outcome='tampered' WHERE sequence=?",
            ((difficulty % event_count) + 1,),
        )
    elif mutation == 1:
        audit._connection.execute(
            "UPDATE audit_events SET actor='attacker@example.com' WHERE sequence=?",
            ((difficulty % event_count) + 1,),
        )
    elif mutation == 2:
        audit._connection.execute(
            "DELETE FROM audit_events WHERE sequence=(SELECT MAX(sequence) FROM audit_events)"
        )
    else:
        audit._connection.execute(
            "UPDATE audit_events SET details='{}' WHERE sequence=?",
            ((difficulty % event_count) + 1,),
        )
    audit._connection.commit()
    detected = audit.verify_chain() is False
    return detected, f"events={event_count}, mutation={mutation}, detected={detected}"


def _payload_unicode_case(root: Path, case_id: int, difficulty: int) -> tuple[bool, str]:
    _, actions, employee, _, _ = _service(root, case_id)
    bad = DANGEROUS_TEXTS[difficulty % len(DANGEROUS_TEXTS)]
    blocked, observed = _blocked(
        lambda: actions.request(
            principal=employee,
            action_name="create_it_service_ticket",
            payload={"summary": f"Ticket {bad}", "description": "Needs review"},
            request_id=f"r-{case_id}",
            idempotency_key=f"unicode-{case_id}",
        ),
        ValueError,
    )
    return blocked, observed


def _audit_unicode_case(root: Path, case_id: int, difficulty: int) -> tuple[bool, str]:
    audit = SQLiteAuditStore(root / f"audit-unicode-{case_id}.db")
    bad = DANGEROUS_TEXTS[difficulty % len(DANGEROUS_TEXTS)]
    blocked, observed = _blocked(
        lambda: audit.record(
            actor=f"user-{bad}@example.com",
            action="rag_query",
            resource=None,
            outcome="grounded",
            request_id=f"r-{case_id}",
            details={},
        ),
        ValueError,
    )
    return blocked, observed


def _audit_nonfinite_case(root: Path, case_id: int, difficulty: int) -> tuple[bool, str]:
    audit = SQLiteAuditStore(root / f"audit-nonfinite-{case_id}.db")
    value = [float("nan"), float("inf"), float("-inf")][difficulty % 3]
    blocked, observed = _blocked(
        lambda: audit.record(
            actor="employee@example.com",
            action="risk_metric",
            resource=f"R-{case_id}",
            outcome="observed",
            request_id=f"r-{case_id}",
            details={"value": value},
        ),
        ValueError,
    )
    return blocked, observed


def run_campaign(total_cases: int = 1000) -> dict[str, Any]:
    if total_cases < 1:
        raise ValueError("total_cases must be positive")

    families = [
        "acl_pre_retrieval",
        "idempotency_conflict",
        "self_approval",
        "requester_execution",
        "orphan_execution_analytics",
        "duplicate_approval_analytics",
        "audit_tamper_detection",
        "payload_unicode_controls",
        "audit_identity_unicode_controls",
        "audit_nonfinite_details",
    ]

    results: list[CampaignCase] = []
    with tempfile.TemporaryDirectory(prefix="nexus-adversarial-") as tmp:
        root = Path(tmp)
        for case_id in range(1, total_cases + 1):
            difficulty = case_id
            tier = ((case_id - 1) // max(1, total_cases // 10)) + 1
            family = families[(case_id - 1) % len(families)]

            noise_ok, noise_observed = _clean_noise_check(difficulty)
            if not noise_ok:
                results.append(
                    CampaignCase(
                        case_id,
                        difficulty,
                        tier,
                        family,
                        False,
                        "benign increasing-noise stream must not create false-positive exceptions",
                        noise_observed,
                        "FALSE_POSITIVE_UNDER_NOISE",
                    )
                )
                continue

            if family == "acl_pre_retrieval":
                passed, observed = _acl_case(root, case_id, difficulty)
                expected = "restricted content never enters semantic or lexical results for unauthorized principal"
                finding = "ACL_RETRIEVAL_LEAK"
            elif family == "idempotency_conflict":
                passed, observed = _idempotency_case(root, case_id, difficulty)
                expected = "changed request under reused idempotency key is rejected and audited"
                finding = "IDEMPOTENCY_CONFLICT_BYPASS"
            elif family == "self_approval":
                passed, observed = _self_approval_case(root, case_id, difficulty)
                expected = "privileged requester cannot self-approve and denial is audited"
                finding = "SELF_APPROVAL_BYPASS"
            elif family == "requester_execution":
                passed, observed = _requester_execution_case(root, case_id, difficulty)
                expected = "privileged requester cannot execute own independently-approved request"
                finding = "REQUESTER_EXECUTION_BYPASS"
            elif family == "orphan_execution_analytics":
                passed, observed = _analytics_case(case_id, difficulty, "orphan_execution")
                expected = "analytics detect execution with neither request nor approval provenance"
                finding = "ORPHAN_EXECUTION_NOT_DETECTED"
            elif family == "duplicate_approval_analytics":
                passed, observed = _analytics_case(case_id, difficulty, "duplicate_approval")
                expected = "analytics detect duplicate approvals amid increasing event noise"
                finding = "DUPLICATE_APPROVAL_NOT_DETECTED"
            elif family == "audit_tamper_detection":
                passed, observed = _audit_tamper_case(root, case_id, difficulty)
                expected = "row modification or tail deletion breaks audit verification"
                finding = "AUDIT_TAMPER_UNDETECTED"
            elif family == "payload_unicode_controls":
                passed, observed = _payload_unicode_case(root, case_id, difficulty)
                expected = "dangerous control/format characters are rejected from human-reviewed action text"
                finding = "PAYLOAD_CONTROL_CHAR_ACCEPTED"
            elif family == "audit_identity_unicode_controls":
                passed, observed = _audit_unicode_case(root, case_id, difficulty)
                expected = "dangerous control/format characters are rejected from audit identity fields"
                finding = "AUDIT_IDENTITY_CONTROL_CHAR_ACCEPTED"
            else:
                passed, observed = _audit_nonfinite_case(root, case_id, difficulty)
                expected = "non-finite numbers are rejected from canonical audit evidence"
                finding = "AUDIT_NONFINITE_ACCEPTED"

            results.append(
                CampaignCase(
                    case_id=case_id,
                    difficulty_score=difficulty,
                    tier=tier,
                    family=family,
                    passed=passed,
                    expected=expected,
                    observed=f"{observed}; {noise_observed}",
                    finding_key=None if passed else finding,
                )
            )

    failed = [r for r in results if not r.passed]
    family_summary: dict[str, dict[str, int]] = {}
    for family in families:
        subset = [r for r in results if r.family == family]
        family_summary[family] = {
            "cases": len(subset),
            "passed": sum(1 for r in subset if r.passed),
            "failed": sum(1 for r in subset if not r.passed),
        }

    finding_counts: dict[str, int] = {}
    for item in failed:
        if item.finding_key:
            finding_counts[item.finding_key] = finding_counts.get(item.finding_key, 0) + 1

    return {
        "campaign": "NEXUS 1000-case escalating adversarial assurance campaign",
        "difficulty_definition": (
            "Cases are numbered 1..N with a strictly increasing difficulty_score. "
            "Each later case is evaluated with one more unrelated audit-event distractor than the previous case; "
            "the primary control family rotates across ten assurance domains."
        ),
        "total_cases": len(results),
        "passed_cases": len(results) - len(failed),
        "failed_cases": len(failed),
        "overall_passed": not failed,
        "max_difficulty_score": results[-1].difficulty_score if results else 0,
        "families": family_summary,
        "finding_counts": finding_counts,
        "failed_case_sample": [asdict(r) for r in failed[:50]],
        "claims_boundary": (
            "This is deterministic adversarial testing of a self-built fictional system. "
            "It is not an independent audit, production penetration test, or evidence of operating effectiveness over a client population."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=1000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = run_campaign(args.cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if not report["overall_passed"]:
        raise SystemExit(
            f"Adversarial campaign exposed {report['failed_cases']} failing cases; see {args.output}"
        )


if __name__ == "__main__":
    main()
