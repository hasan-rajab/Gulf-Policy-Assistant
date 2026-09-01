from pathlib import Path

import pytest

from app.core.access import AccessContext
from app.services.actions import EnterpriseActionService
from app.services.audit import SQLiteAuditStore
from app.services.reranking import PolicyReranker
from app.stores.base import SearchResult, StoredChunk
from app.stores.local import LocalVectorStore


def _chunk(
    chunk_id: str,
    title: str,
    text: str,
    embedding: list[float],
    *,
    visibility: str = "public",
    roles: list[str] | None = None,
    departments: list[str] | None = None,
) -> StoredChunk:
    return StoredChunk(
        id=chunk_id,
        document_id=f"doc-{chunk_id}",
        title=title,
        text=text,
        embedding=embedding,
        chunk_index=0,
        visibility=visibility,
        allowed_roles=roles or [],
        allowed_departments=departments or [],
    )


def test_acl_is_applied_before_local_semantic_search(tmp_path: Path):
    store = LocalVectorStore(tmp_path / "index.json")
    store.upsert(
        [
            _chunk(
                "restricted",
                "Executive Restructuring Plan",
                "confidential restructuring compensation details",
                [1.0, 0.0],
                visibility="restricted",
                roles=["executive"],
            ),
            _chunk(
                "public",
                "General Workplace Guide",
                "general employee workplace information",
                [0.0, 1.0],
            ),
        ]
    )

    employee = AccessContext.create("employee@example.com", ["employee"], ["general"])
    results = store.search([1.0, 0.0], 5, access=employee)

    assert [result.chunk.id for result in results] == ["public"]
    assert all(result.chunk.id != "restricted" for result in results)


def test_acl_allows_matching_role_department_and_admin(tmp_path: Path):
    store = LocalVectorStore(tmp_path / "index.json")
    store.upsert(
        [
            _chunk(
                "hr",
                "HR Restricted Policy",
                "restricted HR policy",
                [1.0, 0.0],
                visibility="restricted",
                departments=["hr"],
            )
        ]
    )

    hr_user = AccessContext.create("hr@example.com", ["employee"], ["hr"])
    admin = AccessContext.create("admin@example.com", ["knowledge_admin"], [])
    outsider = AccessContext.create("ops@example.com", ["employee"], ["operations"])

    assert store.search([1.0, 0.0], 1, access=hr_user)[0].chunk.id == "hr"
    assert store.search([1.0, 0.0], 1, access=admin)[0].chunk.id == "hr"
    assert store.search([1.0, 0.0], 1, access=outsider) == []


def test_acl_is_applied_before_lexical_search_too(tmp_path: Path):
    store = LocalVectorStore(tmp_path / "index.json")
    store.upsert(
        [
            _chunk(
                "secret",
                "Merger Code Name Falcon",
                "Project Falcon acquisition closes on 30 September",
                [0.0, 1.0],
                visibility="restricted",
                roles=["executive"],
            ),
            _chunk(
                "public",
                "Travel Policy",
                "Employees submit travel requests through the portal",
                [1.0, 0.0],
            ),
        ]
    )
    employee = AccessContext.create("employee@example.com", ["employee"], [])

    results = store.hybrid_search(
        "Project Falcon acquisition 30 September",
        [0.0, 1.0],
        5,
        access=employee,
    )

    assert all(result.chunk.id != "secret" for result in results)


def test_reranker_promotes_exact_policy_evidence_without_mutating_confidence():
    reranker = PolicyReranker()
    general = SearchResult(
        chunk=_chunk("general", "Work Guide", "employees work from approved locations", [1.0, 0.0]),
        score=0.90,
    )
    exact = SearchResult(
        chunk=_chunk(
            "exact",
            "Cybersecurity Incident Reporting",
            "Report a cybersecurity incident within 30 minutes through the Security Service Desk",
            [0.0, 1.0],
        ),
        score=0.75,
    )

    ranked = reranker.rerank(
        "cybersecurity incident 30 minutes Security Service Desk",
        [general, exact],
        2,
    )

    assert ranked[0].chunk.id == "exact"
    assert ranked[0].score == 0.75
    assert ranked[0].rerank_score is not None


def test_controlled_action_requires_approval_and_is_idempotent(tmp_path: Path):
    audit = SQLiteAuditStore(tmp_path / "audit.db")
    actions = EnterpriseActionService(tmp_path / "actions.db", audit)
    employee = AccessContext.create("employee@example.com", ["employee"], ["general"])
    admin = AccessContext.create("admin@example.com", ["knowledge_admin"], ["general"])

    requested = actions.request(
        principal=employee,
        action_name="create_it_service_ticket",
        payload={"summary": "VPN access", "description": "Need VPN access for approved remote work"},
        request_id="req-1",
        idempotency_key="vpn-ticket-1",
    )
    duplicate = actions.request(
        principal=employee,
        action_name="create_it_service_ticket",
        payload={"summary": "VPN access", "description": "Need VPN access for approved remote work"},
        request_id="req-2",
        idempotency_key="vpn-ticket-1",
    )

    assert requested["status"] == "pending_approval"
    assert duplicate["id"] == requested["id"]

    with pytest.raises(PermissionError):
        actions.approve(requested["id"], employee, "req-3")
    with pytest.raises(ValueError):
        actions.execute(requested["id"], admin, "req-4")

    approved = actions.approve(requested["id"], admin, "req-5")
    executed = actions.execute(requested["id"], admin, "req-6")

    assert approved["status"] == "approved"
    assert executed["status"] == "executed"
    assert executed["result"]["execution_mode"] == "demo_controlled_handoff"
    assert executed["result"]["external_reference"].startswith("NEXUS-")
    assert audit.verify_chain() is True


def test_action_allowlist_rejects_arbitrary_tool_name(tmp_path: Path):
    audit = SQLiteAuditStore(tmp_path / "audit.db")
    actions = EnterpriseActionService(tmp_path / "actions.db", audit)
    employee = AccessContext.create("employee@example.com", ["employee"], [])

    with pytest.raises(ValueError, match="allowlist"):
        actions.request(
            principal=employee,
            action_name="run_shell_command",
            payload={"command": "whoami"},
            request_id="req-1",
        )


def test_audit_chain_detects_tampering(tmp_path: Path):
    audit = SQLiteAuditStore(tmp_path / "audit.db")
    audit.record(
        actor="employee@example.com",
        action="rag_query",
        resource="conversation-1",
        outcome="grounded",
        request_id="req-1",
        details={"source_count": 2},
    )
    assert audit.verify_chain() is True

    audit._connection.execute(
        "UPDATE audit_events SET outcome='tampered' WHERE sequence=1"
    )
    audit._connection.commit()
    assert audit.verify_chain() is False
