from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from google.cloud import bigquery

from app.core.access import AccessContext
from app.core.config import Settings
from app.services.actions import EnterpriseActionService
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
        if idempotency_key and len(idempotency_key) > 128:
            raise ValueError("Idempotency key is too long")

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
            raise PermissionError("Knowledge administrator permission required")
        row = self._find(action_id)
        if row is None:
            raise KeyError(action_id)
        if row["status"] != "pending_approval":
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
            raise PermissionError("Knowledge administrator permission required")
        row = self._find(action_id)
        if row is None:
            raise KeyError(action_id)
        if row["status"] != "approved":
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
