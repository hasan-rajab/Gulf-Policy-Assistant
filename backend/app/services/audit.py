from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from google.cloud import bigquery

from app.core.config import Settings


class AuditStore(Protocol):
    def record(
        self,
        *,
        actor: str,
        action: str,
        resource: str | None,
        outcome: str,
        request_id: str | None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


def _canonical_event(event: dict[str, Any]) -> str:
    return json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash_event(event: dict[str, Any], previous_hash: str) -> str:
    material = f"{previous_hash}|{_canonical_event(event)}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


class SQLiteAuditStore:
    """Append-only local audit trail with a tamper-evident hash chain."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              event_id TEXT NOT NULL UNIQUE,
              timestamp TEXT NOT NULL,
              actor TEXT NOT NULL,
              action TEXT NOT NULL,
              resource TEXT,
              outcome TEXT NOT NULL,
              request_id TEXT,
              details TEXT NOT NULL,
              previous_hash TEXT NOT NULL,
              event_hash TEXT NOT NULL UNIQUE
            )
            """
        )
        self._connection.commit()

    def record(
        self,
        *,
        actor: str,
        action: str,
        resource: str | None,
        outcome: str,
        request_id: str | None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor.lower(),
            "action": action,
            "resource": resource,
            "outcome": outcome,
            "request_id": request_id,
            "details": details or {},
        }
        with self._lock:
            row = self._connection.execute(
                "SELECT event_hash FROM audit_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous_hash = row[0] if row else "GENESIS"
            event_hash = _hash_event(event, previous_hash)
            self._connection.execute(
                """
                INSERT INTO audit_events (
                  event_id, timestamp, actor, action, resource, outcome,
                  request_id, details, previous_hash, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["event_id"],
                    event["timestamp"],
                    event["actor"],
                    event["action"],
                    event["resource"],
                    event["outcome"],
                    event["request_id"],
                    _canonical_event(event["details"]),
                    previous_hash,
                    event_hash,
                ),
            )
            self._connection.commit()
        return {**event, "previous_hash": previous_hash, "event_hash": event_hash}

    def verify_chain(self) -> bool:
        rows = self._connection.execute(
            """
            SELECT event_id, timestamp, actor, action, resource, outcome,
                   request_id, details, previous_hash, event_hash
            FROM audit_events ORDER BY sequence ASC
            """
        ).fetchall()
        expected_previous = "GENESIS"
        for row in rows:
            details = json.loads(row[7])
            event = {
                "event_id": row[0],
                "timestamp": row[1],
                "actor": row[2],
                "action": row[3],
                "resource": row[4],
                "outcome": row[5],
                "request_id": row[6],
                "details": details,
            }
            if row[8] != expected_previous:
                return False
            if row[9] != _hash_event(event, expected_previous):
                return False
            expected_previous = row[9]
        return True


class BigQueryAuditStore:
    """Append audit events to the production BigQuery audit table."""

    def __init__(self, settings: Settings):
        self.client = bigquery.Client(project=settings.google_cloud_project, location=settings.bq_location)
        self.table = settings.bq_audit_table_fqn

    def _latest_hash(self) -> str:
        rows = self.client.query(
            f"SELECT event_hash FROM `{self.table}` ORDER BY timestamp DESC LIMIT 1"
        ).result()
        row = next(iter(rows), None)
        return str(row.event_hash) if row else "GENESIS"

    def record(
        self,
        *,
        actor: str,
        action: str,
        resource: str | None,
        outcome: str,
        request_id: str | None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor.lower(),
            "action": action,
            "resource": resource,
            "outcome": outcome,
            "request_id": request_id,
            "details": details or {},
        }
        previous_hash = self._latest_hash()
        event_hash = _hash_event(event, previous_hash)
        row = {
            **event,
            "details": _canonical_event(event["details"]),
            "previous_hash": previous_hash,
            "event_hash": event_hash,
        }
        errors = self.client.insert_rows_json(self.table, [row])
        if errors:
            raise RuntimeError(f"BigQuery audit insert failed: {errors}")
        return {**event, "previous_hash": previous_hash, "event_hash": event_hash}
