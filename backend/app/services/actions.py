from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.access import AccessContext
from app.services.audit import AuditStore


ACTION_REGISTRY = {
    "create_it_service_ticket": {
        "required_fields": {"summary", "description"},
        "allowed_fields": {"summary", "description", "priority"},
        "description": "Create an IT service request after human approval.",
    },
    "request_hr_policy_review": {
        "required_fields": {"policy_question", "business_reason"},
        "allowed_fields": {"policy_question", "business_reason"},
        "description": "Request HR review of a policy interpretation after human approval.",
    },
    "request_policy_exception": {
        "required_fields": {"policy", "exception_reason", "duration"},
        "allowed_fields": {"policy", "exception_reason", "duration"},
        "description": "Submit a policy-exception request after explicit administrator approval.",
    },
}


class EnterpriseActionService:
    """Allowlisted, approval-gated enterprise action execution.

    This deliberately does not allow arbitrary URLs, shell commands, SQL, or
    model-generated tool names. Every action is registered and schema-checked,
    and execution requires a separate administrator approval state transition.
    """

    def __init__(self, path: Path, audit: AuditStore):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.audit = audit
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS action_requests (
              id TEXT PRIMARY KEY,
              requester TEXT NOT NULL,
              action_name TEXT NOT NULL,
              payload TEXT NOT NULL,
              idempotency_key TEXT,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              approved_at TEXT,
              approved_by TEXT,
              executed_at TEXT,
              result TEXT,
              UNIQUE(requester, idempotency_key)
            )
            """
        )
        self._connection.commit()

    @staticmethod
    def _validate_payload(action_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        spec = ACTION_REGISTRY.get(action_name)
        if spec is None:
            raise ValueError("Action is not in the enterprise allowlist")
        keys = set(payload)
        missing = spec["required_fields"] - keys
        extras = keys - spec["allowed_fields"]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")
        if extras:
            raise ValueError(f"Unsupported fields: {', '.join(sorted(extras))}")

        clean: dict[str, Any] = {}
        for key, value in payload.items():
            if not isinstance(value, (str, int, float, bool)):
                raise ValueError(f"Field '{key}' must be a scalar value")
            text = str(value).strip()
            if not text or len(text) > 2000:
                raise ValueError(f"Field '{key}' is empty or too long")
            clean[key] = text
        return clean

    def request(
        self,
        *,
        principal: AccessContext,
        action_name: str,
        payload: dict[str, Any],
        request_id: str | None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        clean = self._validate_payload(action_name, payload)
        if idempotency_key and len(idempotency_key) > 128:
            raise ValueError("Idempotency key is too long")

        with self._lock:
            if idempotency_key:
                existing = self._connection.execute(
                    "SELECT * FROM action_requests WHERE requester=? AND idempotency_key=?",
                    (principal.email, idempotency_key),
                ).fetchone()
                if existing:
                    return self._row_to_dict(existing)

            action_id = str(uuid4())
            created_at = datetime.now(timezone.utc).isoformat()
            self._connection.execute(
                """
                INSERT INTO action_requests
                (id, requester, action_name, payload, idempotency_key, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending_approval', ?)
                """,
                (
                    action_id,
                    principal.email,
                    action_name,
                    json.dumps(clean, ensure_ascii=False, sort_keys=True),
                    idempotency_key,
                    created_at,
                ),
            )
            self._connection.commit()

        self.audit.record(
            actor=principal.email,
            action="enterprise_action_requested",
            resource=action_id,
            outcome="pending_approval",
            request_id=request_id,
            details={"action_name": action_name, "payload_fields": sorted(clean)},
        )
        return self.get(action_id, principal)

    def approve(
        self,
        action_id: str,
        approver: AccessContext,
        request_id: str | None,
    ) -> dict[str, Any]:
        if not approver.is_admin:
            raise PermissionError("Knowledge administrator permission required")
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM action_requests WHERE id=?",
                (action_id,),
            ).fetchone()
            if row is None:
                raise KeyError(action_id)
            if row["status"] != "pending_approval":
                raise ValueError(f"Action cannot be approved from status {row['status']}")
            approved_at = datetime.now(timezone.utc).isoformat()
            self._connection.execute(
                """
                UPDATE action_requests
                SET status='approved', approved_at=?, approved_by=?
                WHERE id=?
                """,
                (approved_at, approver.email, action_id),
            )
            self._connection.commit()

        self.audit.record(
            actor=approver.email,
            action="enterprise_action_approved",
            resource=action_id,
            outcome="approved",
            request_id=request_id,
            details={"requester": row["requester"], "action_name": row["action_name"]},
        )
        return self.get(action_id, approver)

    def execute(
        self,
        action_id: str,
        executor: AccessContext,
        request_id: str | None,
    ) -> dict[str, Any]:
        if not executor.is_admin:
            raise PermissionError("Knowledge administrator permission required")
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM action_requests WHERE id=?",
                (action_id,),
            ).fetchone()
            if row is None:
                raise KeyError(action_id)
            if row["status"] != "approved":
                raise ValueError(f"Action cannot execute from status {row['status']}")

            # Portfolio-safe executor: produces a deterministic external-system
            # handoff artifact instead of pretending to call a live HR/IT system.
            result = {
                "execution_mode": "demo_controlled_handoff",
                "external_reference": f"NEXUS-{action_id.split('-')[0].upper()}",
                "action_name": row["action_name"],
            }
            executed_at = datetime.now(timezone.utc).isoformat()
            self._connection.execute(
                """
                UPDATE action_requests
                SET status='executed', executed_at=?, result=?
                WHERE id=?
                """,
                (json.dumps(result, sort_keys=True), executed_at, action_id),
            )
            self._connection.commit()

        self.audit.record(
            actor=executor.email,
            action="enterprise_action_executed",
            resource=action_id,
            outcome="executed",
            request_id=request_id,
            details=result,
        )
        return self.get(action_id, executor)

    def get(self, action_id: str, principal: AccessContext) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT * FROM action_requests WHERE id=?",
            (action_id,),
        ).fetchone()
        if row is None:
            raise KeyError(action_id)
        if row["requester"] != principal.email and not principal.is_admin:
            raise PermissionError("Action request belongs to another user")
        return self._row_to_dict(row)

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "requester": row["requester"],
            "action_name": row["action_name"],
            "payload": json.loads(row["payload"]),
            "status": row["status"],
            "created_at": row["created_at"],
            "approved_at": row["approved_at"],
            "approved_by": row["approved_by"],
            "executed_at": row["executed_at"],
            "result": json.loads(row["result"]) if row["result"] else None,
        }
