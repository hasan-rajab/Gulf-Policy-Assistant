# NEXUS Security Model

NEXUS treats enterprise retrieval as an authorization problem before it treats it as a ranking problem.

## Trust boundaries

1. **Identity** — demo JWT or enterprise IAP provides a stable user email.
2. **Entitlements** — roles and departments are resolved server-side from trusted configuration/directory data. Client-supplied role headers are ignored.
3. **Retrieval authorization** — visibility, role ACLs, and department ACLs reduce the searchable corpus before semantic or lexical scoring.
4. **Grounding** — only authorized retrieved chunks can reach the generator or citation layer.
5. **Actions** — side-effecting workflows use a fixed allowlist and require an explicit administrator approval transition before execution.
6. **Audit** — authentication, RAG access, ingestion, evaluation, approval, and execution events are appended to a durable audit store.

## Document policy

Each chunk carries:

- `visibility`: `public` or `restricted`
- `allowed_roles`: explicit role grants
- `allowed_departments`: explicit department grants

A restricted document without an explicit business grant is treated as administrator-only.

## Local retrieval

The local vector store creates an authorized chunk set first. Semantic cosine scoring and lexical matching operate only on that set. Restricted content is never scored for an unauthorized principal.

## BigQuery retrieval

The BigQuery backend passes a filtered base-table query into `VECTOR_SEARCH`. ACL columns are included in the vector index `STORING(...)` list so authorization can be used as an efficient search pre-filter.

## Controlled actions

The current portfolio executor exposes only:

- `create_it_service_ticket`
- `request_hr_policy_review`
- `request_policy_exception`

Arbitrary tool names, URLs, shell commands, SQL, nested objects, and unknown fields are rejected. Requests are persisted with an idempotency key, then move through:

`pending_approval -> approved -> executed`

The demo executor creates an external-system handoff reference. It does not pretend to call a live HR or IT platform.

## Audit integrity

Local audit events are stored in SQLite with an append-only sequence and SHA-256 hash chain. A verification function recalculates the chain and detects modified rows. The BigQuery production path appends the same event envelope to a partitioned audit table for warehouse retention and external governance controls.

## Failure behavior

- unauthorized documents are absent from retrieval candidates
- insufficient authorized evidence causes abstention
- non-admin ingestion is rejected
- non-admin evaluation is rejected to protect cost and evaluation integrity
- non-admin approval/execution is rejected
- actions cannot execute before approval
- action request IDs are idempotent per requester
