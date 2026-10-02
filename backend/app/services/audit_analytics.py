from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


def analyze_audit_events(
    events: Iterable[dict[str, Any]],
    *,
    failed_login_threshold: int = 3,
) -> dict[str, Any]:
    """Run deterministic control-exception analytics over NEXUS audit events.

    The analytics are intentionally simple and explainable. They are designed
    for assurance/testing evidence, not as a replacement for a production SIEM.
    """
    ordered = list(events)
    approvals: set[str] = set()
    executions: set[str] = set()
    requests: dict[str, str] = {}
    failed_logins: Counter[str] = Counter()
    exceptions: list[dict[str, Any]] = []

    for event in ordered:
        action = str(event.get("action") or "")
        resource = event.get("resource")
        actor = str(event.get("actor") or "").lower()
        outcome = str(event.get("outcome") or "")
        details = event.get("details") or {}

        if action == "enterprise_action_requested" and resource:
            requests[str(resource)] = actor

        elif action == "enterprise_action_approved" and resource:
            resource_id = str(resource)
            requester = str(details.get("requester") or requests.get(resource_id) or "").lower()

            if resource_id not in requests:
                exceptions.append(
                    {
                        "type": "APPROVAL_WITHOUT_REQUEST",
                        "resource": resource_id,
                        "actor": actor,
                        "severity": "high",
                        "reason": "approval event has no prior request event in the analyzed sequence",
                    }
                )

            if resource_id in approvals:
                exceptions.append(
                    {
                        "type": "DUPLICATE_APPROVAL",
                        "resource": resource_id,
                        "actor": actor,
                        "severity": "high",
                        "reason": "more than one approval event was recorded for the same action",
                    }
                )

            if requester and requester == actor:
                exceptions.append(
                    {
                        "type": "SELF_APPROVAL",
                        "resource": resource_id,
                        "actor": actor,
                        "severity": "high",
                        "reason": "requester and approver are the same principal",
                    }
                )
            approvals.add(resource_id)

        elif action == "enterprise_action_executed" and resource:
            resource_id = str(resource)
            requester = requests.get(resource_id, "")

            if resource_id not in requests:
                exceptions.append(
                    {
                        "type": "EXECUTION_WITHOUT_REQUEST",
                        "resource": resource_id,
                        "actor": actor,
                        "severity": "critical",
                        "reason": "execution event has no prior request event in the analyzed sequence",
                    }
                )

            if resource_id not in approvals:
                exceptions.append(
                    {
                        "type": "EXECUTION_WITHOUT_RECORDED_APPROVAL",
                        "resource": resource_id,
                        "actor": actor,
                        "severity": "critical",
                        "reason": "execution event has no prior approval event in the analyzed sequence",
                    }
                )

            if resource_id in executions:
                exceptions.append(
                    {
                        "type": "DUPLICATE_EXECUTION",
                        "resource": resource_id,
                        "actor": actor,
                        "severity": "critical",
                        "reason": "more than one execution event was recorded for the same action",
                    }
                )

            if requester and requester == actor:
                exceptions.append(
                    {
                        "type": "REQUESTER_EXECUTION",
                        "resource": resource_id,
                        "actor": actor,
                        "severity": "high",
                        "reason": "requester executed their own action",
                    }
                )

            executions.add(resource_id)

        elif action == "login" and outcome == "denied":
            failed_logins[actor or "unknown"] += 1

    for actor, count in sorted(failed_logins.items()):
        if count >= failed_login_threshold:
            exceptions.append(
                {
                    "type": "REPEATED_DENIED_LOGIN",
                    "resource": None,
                    "actor": actor,
                    "severity": "medium",
                    "reason": f"{count} denied login events met or exceeded threshold {failed_login_threshold}",
                }
            )

    return {
        "event_count": len(ordered),
        "exception_count": len(exceptions),
        "exceptions": exceptions,
        "failed_login_counts": dict(sorted(failed_logins.items())),
        "approved_action_count": len(approvals),
        "executed_action_count": len(executions),
    }
