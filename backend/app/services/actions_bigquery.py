from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from google.cloud import bigquery

from app.core.access import AccessContext
from app.core.config import Settings
from app.services.actions import EnterpriseActionService, _contains_unsafe_text_control
from app.services.audit import AuditStore


class BigQueryEnterpriseActionService:
    """Durable cloud action workflow using guarded BigQuery DML transitions."""

    def __init__(self, settings: Settings, audit: AuditStore):
        self.audit = audit
        self.client = bigquery.Client(
            project=settings.google_cloud_project,
            location=settings.bq_location,
        )
        self.table = settings.bq_actions_table_fqn

    @staticmethod
    def _params(**values: tuple[str, Any]) -> list:
        return [
            bigquery.ScalarQueryParameter(name, type_name, value)
            for name, (type_name, value) in values.items()
        ]

    def _query(self, sql: str, params: list | None = None):
        return self.client.query(
            sql,
            job_config=bigquery.QueryJobConfig(query_parameters=params or []),
        )

    def _record_denial(
        self,
        *,
        actor: str,
        action: str,
        action_id: str,
        request_id: str | None,
        reason: str,
        status_value: str | None = None,
    ) -> None:
        details: dict[str, Any] = {"reason": reason}
        if status_value is not None:
            details["current_status"] = status_value
        self.audit.record(
            actor=actor,
            action=action,
            resource=action_id,
            outcome="denied",
            request_id=request_id,
            details=details,
        )

    def request(
        self,
        *,
        principal: AccessContext,
        action_name: str,
        payload: dict[str, Any],
        request_id: str | None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        clean = EnterpriseActionService._validate_payload(action_name, payload)
        if idempotency_key is not None:
            idempotency_key = idempotency_key.strip()
            if not idempotency_key:
                raise ValueError("Idempotency key cannot be blank")
            if len(idempotency_key) > 128:
                raise ValueError("Idempotency key is too long")
            if _contains_unsafe_text_control(idempotency_key):
                raise ValueError("Idempotency key contains unsafe control/format characters")

        action_id = str(uuid4())
        created_at = datetime.now(timezone.utc)
        payload_json = json.dumps(clean, ensure_ascii=False, sort_keys=True)

        if idempotency_key:
            merge_condition = "T.requester = S.requester AND T.idempotency_key = S.idempotency_key"
        else:
            merge_condition = "T.id = S.id"

        sql = f"""
        MERGE `{self.table}` T
        USING (
          SELECT @id AS id, @requester AS requester, @action_name AS action_name,
                 @payload AS payload, @idempotency_key AS idempotency_key,
                 @created_at AS created_at
        ) S
        ON {merge_condition}
        WHEN NOT MATCHED THEN
          INSERT (id, requester, action_name, payload, idempotency_key, status, created_at)
          VALUES (S.id, S.requester, S.action_name, S.payload, S.idempotency_key,
                  'pending_approval', S.created_at)
        """
        params = self._params(
            id=("STRING", action_id),
            requester=("STRING", principal.email),
            action_name=("STRING", action_name),
            payload=("STRING", payload_json),
            idempotency_key=("STRING", idempotency_key),
            created_at=("TIMESTAMP", created_at),
        )
        self._query(sql, params).result()

        if idempotency_key:
            row = self._find_by_idempotency(principal.email, idempotency_key)
        else:
            row = self._find(action_id)
        if row is None:
            raise RuntimeError("Action request was not persisted")

        if row["id"] != action_id:
            if row["action_name"] != action_name or row["payload"] != clean:
                self._record_denial(
                    actor=principal.email,
                    action="enterprise_action_request_rejected",
                    action_id=row["id"],
                    request_id=request_id,
                    reason="idempotency_key_conflict",
                    status_value=row["status"],
                )
                raise ValueError("Idempotency key conflict: key was already used for a different request")

        if row["id"] == action_id:
            self.audit.record(
                actor=principal.email,
                action="enterprise_action_requested",
                resource=action_id,
                outcome="pending_approval",
                request_id=request_id,
                details={"action_name": action_name, "payload_fields": sorted(clean)},
            )
        return self._authorize_row(row, principal)

    def approve(
        self,
        action_id: str,
        approver: AccessContext,
        request_id: str | None,
    ) -> dict[str, Any]:
        if not approver.is_admin:
            self._record_denial(
                actor=approver.email,
                action="enterprise_action_approval_attempt",
                action_id=action_id,
                request_id=request_id,
                reason="insufficient_privilege",
            )
            raise PermissionError("Knowledge administrator permission required")

        row = self._find(action_id)
        if row is None:
            raise KeyError(action_id)

        if row["requester"].lower() == approver.email.lower():
            self._record_denial(
                actor=approver.email,
                action="enterprise_action_approval_attempt",
                action_id=action_id,
                request_id=request_id,
                reason="self_approval_prohibited",
                status_value=row["status"],
            )
            raise PermissionError("Requester cannot approve their own action")

        if row["status"] != "pending_approval":
            self._record_denial(
                actor=approver.email,
                action="enterprise_action_approval_attempt",
                action_id=action_id,
                request_id=request_id,
                reason="invalid_state_transition",
                status_value=row["status"],
            )
            raise ValueError(f"Action cannot be approved from status {row['status']}")

        approved_at = datetime.now(timezone.utc)
        job = self._query(
            f"""
            UPDATE `{self.table}`
            SET status='approved', approved_at=@approved_at, approved_by=@approved_by
            WHERE id=@id AND status='pending_approval'
            """,
            self._params(
                approved_at=("TIMESTAMP", approved_at),
                approved_by=("STRING", approver.email),
                id=("STRING", action_id),
            ),
        )
        job.result()
        if not job.num_dml_affected_rows:
            current = self._find(action_id)
            state = current["status"] if current else "missing"
            raise ValueError(f"Action approval lost a concurrent state transition; current status {state}")

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
            self._record_denial(
                actor=executor.email,
                action="enterprise_action_execution_attempt",
                action_id=action_id,
                request_id=request_id,
                reason="insufficient_privilege",
            )
            raise PermissionError("Knowledge administrator permission required")

        row = self._find(action_id)
        if row is None:
            raise KeyError(action_id)

        if row["status"] == "approved":
            approved_by = str(row["approved_by"] or "").strip().lower()
            approved_at = str(row["approved_at"] or "").strip()
            if not approved_by or not approved_at or approved_by == row["requester"].lower():
                self._record_denial(
                    actor=executor.email,
                    action="enterprise_action_execution_attempt",
                    action_id=action_id,
                    request_id=request_id,
                    reason="invalid_approval_metadata",
                    status_value=row["status"],
                )
                raise ValueError("Action approval metadata is invalid")

        if row["requester"].lower() == executor.email.lower():
            self._record_denial(
                actor=executor.email,
                action="enterprise_action_execution_attempt",
                action_id=action_id,
                request_id=request_id,
                reason="requester_execution_prohibited",
                status_value=row["status"],
            )
            raise PermissionError("Requester cannot execute their own action")

        if row["status"] != "approved":
            self._record_denial(
                actor=executor.email,
                action="enterprise_action_execution_attempt",
                action_id=action_id,
                request_id=request_id,
                reason="approval_required",
                status_value=row["status"],
            )
            raise ValueError(f"Action cannot execute from status {row['status']}")

        result = {
            "execution_mode": "demo_controlled_handoff",
            "external_reference": f"NEXUS-{action_id.split('-')[0].upper()}",
            "action_name": row["action_name"],
        }
        executed_at = datetime.now(timezone.utc)
        job = self._query(
            f"""
            UPDATE `{self.table}`
            SET status='executed', executed_at=@executed_at, result=@result
            WHERE id=@id AND status='approved'
            """,
            self._params(
                executed_at=("TIMESTAMP", executed_at),
                result=("STRING", json.dumps(result, sort_keys=True)),
                id=("STRING", action_id),
            ),
        )
        job.result()
        if not job.num_dml_affected_rows:
            current = self._find(action_id)
            state = current["status"] if current else "missing"
            raise ValueError(f"Action execution lost a concurrent state transition; current status {state}")

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
        row = self._find(action_id)
        if row is None:
            raise KeyError(action_id)
        return self._authorize_row(row, principal)

    def _authorize_row(self, row: dict[str, Any], principal: AccessContext) -> dict[str, Any]:
        if row["requester"] != principal.email and not principal.is_admin:
            raise PermissionError("Action request belongs to another user")
        return row

    def _find(self, action_id: str) -> dict[str, Any] | None:
        rows = self._query(
            f"SELECT * FROM `{self.table}` WHERE id=@id LIMIT 1",
            self._params(id=("STRING", action_id)),
        ).result()
        row = next(iter(rows), None)
        return self._row_to_dict(row) if row else None

    def _find_by_idempotency(self, requester: str, idempotency_key: str) -> dict[str, Any] | None:
        rows = self._query(
            f"""
            SELECT * FROM `{self.table}`
            WHERE requester=@requester AND idempotency_key=@idempotency_key
            ORDER BY created_at ASC LIMIT 1
            """,
            self._params(
                requester=("STRING", requester),
                idempotency_key=("STRING", idempotency_key),
            ),
        ).result()
        row = next(iter(rows), None)
        return self._row_to_dict(row) if row else None

    @staticmethod
    def _iso(value: Any) -> str | None:
        if value is None:
            return None
        return value.isoformat() if hasattr(value, "isoformat") else str(value)

    @classmethod
    def _row_to_dict(cls, row) -> dict[str, Any]:
        return {
            "id": row.id,
            "requester": row.requester,
            "action_name": row.action_name,
            "payload": json.loads(row.payload),
            "status": row.status,
            "created_at": cls._iso(row.created_at),
            "approved_at": cls._iso(row.approved_at),
            "approved_by": row.approved_by,
            "executed_at": cls._iso(row.executed_at),
            "result": json.loads(row.result) if row.result else None,
        }
