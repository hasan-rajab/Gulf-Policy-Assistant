from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import unicodedata
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
    # Audit evidence must remain standards-compliant JSON. Reject NaN/Infinity
    # rather than serializing implementation-specific non-finite literals.
    return json.dumps(
        event,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
        allow_nan=False,
    )


def _hash_event(event: dict[str, Any], previous_hash: str) -> str:
    material = f"{previous_hash}|{_canonical_event(event)}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _validate_event_fields(*, actor: str, action: str, outcome: str) -> tuple[str, str, str]:
    actor_n = str(actor).strip().lower()
    action_n = str(action).strip()
    outcome_n = str(outcome).strip()
    for field_name, value in (("actor", actor_n), ("action", action_n), ("outcome", outcome_n)):
        if not value:
            raise ValueError(f"Audit field '{field_name}' must be non-empty")
        if any(unicodedata.category(ch) in {"Cc", "Cf"} for ch in value):
            raise ValueError(
                f"Audit field '{field_name}' contains unsafe control/format characters"
            )
    return actor_n, action_n, outcome_n


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
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_chain_state (
              singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
              event_count INTEGER NOT NULL,
              last_event_hash TEXT NOT NULL
            )
            """
        )
        state = self._connection.execute(
            "SELECT event_count, last_event_hash FROM audit_chain_state WHERE singleton_id=1"
        ).fetchone()
        if state is None:
            last = self._connection.execute(
                "SELECT sequence, event_hash FROM audit_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            count_row = self._connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()
            event_count = int(count_row[0] or 0)
            last_hash = str(last[1]) if last else "GENESIS"
            self._connection.execute(
                "INSERT INTO audit_chain_state(singleton_id, event_count, last_event_hash) VALUES (1, ?, ?)",
                (event_count, last_hash),
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
        actor_n, action_n, outcome_n = _validate_event_fields(actor=actor, action=action, outcome=outcome)
        event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor_n,
            "action": action_n,
            "resource": resource,
            "outcome": outcome_n,
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
            self._connection.execute(
                "UPDATE audit_chain_state SET event_count=event_count+1, last_event_hash=? WHERE singleton_id=1",
                (event_hash,),
            )
            self._connection.commit()
        return {**event, "previous_hash": previous_hash, "event_hash": event_hash}

    def list_events(self) -> list[dict[str, Any]]:
        """Return ordered local audit events for deterministic assurance analytics."""
        rows = self._connection.execute(
            """
            SELECT sequence, event_id, timestamp, actor, action, resource, outcome,
                   request_id, details, previous_hash, event_hash
            FROM audit_events ORDER BY sequence ASC
            """
        ).fetchall()
        return [
            {
                "sequence": row[0],
                "event_id": row[1],
                "timestamp": row[2],
                "actor": row[3],
                "action": row[4],
                "resource": row[5],
                "outcome": row[6],
                "request_id": row[7],
                "details": json.loads(row[8]),
                "previous_hash": row[9],
                "event_hash": row[10],
            }
            for row in rows
        ]

    def verify_chain(self) -> bool:
        rows = self._connection.execute(
            """
            SELECT event_id, timestamp, actor, action, resource, outcome,
                   request_id, details, previous_hash, event_hash
            FROM audit_events ORDER BY sequence ASC
            """
        ).fetchall()
        state = self._connection.execute(
            "SELECT event_count, last_event_hash FROM audit_chain_state WHERE singleton_id=1"
        ).fetchone()
        if state is None:
            return False

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

        actual_count = len(rows)
        actual_last_hash = expected_previous if rows else "GENESIS"
        return actual_count == int(state[0]) and actual_last_hash == str(state[1])


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
        actor_n, action_n, outcome_n = _validate_event_fields(actor=actor, action=action, outcome=outcome)
        event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor_n,
            "action": action_n,
            "resource": resource,
            "outcome": outcome_n,
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
