# NEXUS Enterprise AI

**Governed bilingual enterprise RAG with retrieval-time authorization, grounded evidence, auditable decisions, and approval-gated actions.**

NEXUS is a production-oriented AI engineering reference architecture for a fictional GCC enterprise. It answers Arabic and English policy questions, but its core engineering problem is larger than question answering:

> **How do you let an LLM use enterprise knowledge and enterprise tools without giving it access to information or actions the user is not authorized to use?**

The system therefore treats **identity → authorization → retrieval → grounding → generation → action approval → audit** as one controlled pipeline.

> This repository retains its original GitHub name for continuity. The current application and architecture are NEXUS v2.

---

## What NEXUS demonstrates

### Enterprise RAG
- Arabic/English question answering
- document parsing, chunking, metadata, embeddings, and source provenance
- local semantic + lexical retrieval fused with Reciprocal Rank Fusion (RRF)
- BigQuery Vector Search production path
- deterministic second-stage reranking
- inline `[S#]` citations
- evidence thresholding and safe abstention
- prompt-injection-resistant policy orchestration

### Security and governance
- server-side user role and department resolution
- **retrieval-time document ACL enforcement**
- restricted chunks removed before semantic or lexical scoring
- admin-only knowledge ingestion and evaluation
- client-supplied role/department claims ignored
- document visibility and ACL metadata persisted with every chunk
- query text represented by SHA-256 in the compliance audit rather than copied verbatim

### Controlled enterprise actions
- fixed action allowlist
- strict payload schemas
- idempotent action requests
- persisted `pending_approval → approved → executed` state machine
- knowledge-administrator approval required before execution
- guarded state transitions to prevent approval bypass/concurrent replay
- local SQLite workflow store
- durable BigQuery workflow store for Cloud Run mode
- portfolio-safe external-system handoff instead of pretending a live HR/IT integration exists

### Auditability and quality
- durable local SQLite audit trail with SHA-256 hash-chain verification
- BigQuery audit-event production path
- request IDs and structured application logs
- retrieval/grounding/citation/language regression evaluation
- citation-to-returned-source integrity checks
- security regression tests
- GitHub Actions release gates

---

# Architecture

```text
                     ┌───────────────────────────┐
                     │ Enterprise identity       │
                     │ IAP / local demo JWT      │
                     └─────────────┬─────────────┘
                                   │
                                   ▼
                     ┌───────────────────────────┐
                     │ Server-side entitlements  │
                     │ roles + departments       │
                     └─────────────┬─────────────┘
                                   │
                                   ▼
                     ┌───────────────────────────┐
                     │ Retrieval-time ACL scope  │
                     │ unauthorized chunks gone  │
                     └─────────────┬─────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
          ┌──────────────────┐          ┌──────────────────┐
          │ Semantic search  │          │ Lexical search   │
          │ local / BigQuery │          │ local mode       │
          └────────┬─────────┘          └────────┬─────────┘
                   └──────────────┬──────────────┘
                                  ▼
                           RRF candidates
                                  │
                                  ▼
                     ┌───────────────────────────┐
                     │ Deterministic reranker    │
                     │ confidence + coverage +   │
                     │ title + language          │
                     └─────────────┬─────────────┘
                                   │
                                   ▼
                       calibrated evidence gate
                            │              │
                          enough        insufficient
                            │              │
                            ▼              ▼
                  grounded generation   abstention /
                     + citations        human escalation
                            │
                            ▼
                       audit event

Separate side-effect plane:

employee request
      ↓
allowlist + schema validation
      ↓
pending_approval
      ↓
knowledge_admin approval
      ↓
approved
      ↓
guarded execution
      ↓
audited NEXUS handoff reference
```

## Critical design rule: authorization happens before retrieval

A common RAG mistake is to retrieve broadly and filter restricted documents afterward. NEXUS does not do that.

In local mode, the vector store constructs an authorized chunk set first; cosine scoring and lexical matching run only on that set.

In the BigQuery path, role/department ACLs are first-class table columns and are stored with the vector index. The search passes an ACL-filtered base-table query into `VECTOR_SEARCH`, keeping restricted rows outside the candidate corpus.

This protects against sensitive chunks leaking into model context, reranking, citations, traces, or downstream caches before a post-filter can remove them.

---

# Retrieval pipeline

NEXUS deliberately separates **ranking quality** from **evidence sufficiency**.

1. Resolve the authenticated user's role/department access context.
2. Scope the corpus to authorized chunks.
3. Retrieve a larger candidate set.
4. In local mode, fuse semantic and lexical rankings with RRF.
5. Reject candidates below the calibrated relevance threshold.
6. Rerank qualified evidence using:
   - original retrieval confidence — 55%
   - query/body token coverage — 30%
   - title overlap — 10%
   - language alignment — 5%
7. Return top-k evidence.
8. Generate only when grounded evidence exists; otherwise abstain.

The reranker improves ordering **without overwriting the original retrieval confidence used by the grounding gate**.

---

# Controlled action plane

NEXUS does not treat an LLM answer as permission to change an enterprise system.

Currently registered actions are:

```text
create_it_service_ticket
request_hr_policy_review
request_policy_exception
```

Unknown tool names, shell commands, arbitrary URLs, SQL, nested payload objects, and unregistered fields are rejected.

The portfolio executor intentionally produces a deterministic `NEXUS-*` handoff reference rather than claiming to call a live enterprise platform. A real ServiceNow, Jira, HRIS, or workflow adapter can replace the final executor while retaining the authorization, approval, idempotency, and audit contracts.

### Persistence

- **Local mode:** SQLite action database.
- **Google Cloud mode:** partitioned BigQuery action table with atomic `MERGE` request creation and guarded DML state transitions.

---

# Audit model

NEXUS records meaningful control-plane events including:

- login success/denial
- RAG queries and grounding outcomes
- document ingestion
- evaluation runs
- action requests
- approvals
- executions

For RAG access events, the audit trail stores the query SHA-256 plus source document IDs/count rather than duplicating the full natural-language query into the governance log.

Local audit rows are linked with `previous_hash → event_hash`; `GET /api/audit/verify` recalculates the chain and detects modifications. The BigQuery production path provides durable warehouse retention for the same event envelope and should be combined with customer-specific IAM and retention controls.

---

# Verified NEXUS v2 regression results

Verified by GitHub Actions on **1 September 2026** on the deterministic fictional demo corpus:

### Engineering tests

- **14/14 backend + security tests passed**
- Python compilation passed
- sample-corpus ingestion passed
- Next.js production build passed

### Strict RAG evaluation — 8/8 cases

| Metric | Result |
| --- | ---: |
| Retrieval hit@k | **1.000** |
| Citation rate | **1.000** |
| Citation-to-source integrity | **1.000** |
| Grounding decision accuracy | **1.000** |
| Language match rate | **1.000** |
| Grounded keyword coverage | **1.000** |
| Average deterministic local latency | **2.125 ms** |

The evaluation includes Arabic/English policy questions, unsupported-question abstention, and an adversarial instruction asking the assistant to ignore company policy.

**These numbers are deterministic regression evidence for the bundled fictional corpus. They are not production accuracy, latency, or safety guarantees.**

---

# Security regression coverage

The test suite explicitly verifies that:

- an unauthorized restricted chunk is excluded even when it has the highest semantic similarity
- an exact lexical match to restricted information is still excluded
- matching department access can retrieve a restricted document
- a knowledge administrator can retrieve restricted documents
- an outsider cannot
- reranking does not mutate the original grounding confidence
- arbitrary action names are rejected
- action execution is impossible before approval
- only an administrator can approve
- idempotency prevents duplicate action requests
- the audit hash chain verifies successfully
- modifying a stored audit event causes verification to fail

---

# Local quick start

```bash
cp .env.example .env
docker compose up --build
```

Open:

- NEXUS UI: `http://localhost:3000`
- API: `http://localhost:8080`
- OpenAPI: `http://localhost:8080/docs`

### Employee demo

```text
employee@gulfhorizon.local
Demo123!
```

Employee permissions demonstrate authorized RAG and controlled-action requests.

### Knowledge administrator demo

```text
admin@gulfhorizon.local
Admin123!
```

The knowledge-admin identity additionally demonstrates restricted-document access, ingestion, evaluation, audit verification, approval, and action execution.

Change all demo credentials before any shared environment.

---

# Google Cloud reference path

```text
Employee
   ↓
Cloud Run web tier protected by IAP
   ↓
private Cloud Run FastAPI service
   ↓
trusted identity → server-side access profile
   ↓
ACL-prefiltered BigQuery Vector Search
   ↓
reranking + evidence threshold
   ↓
Gemini grounded generation
   ↓
response + BigQuery audit events

Controlled actions
   ↓
BigQuery action workflow state
   ↓
admin approval → guarded execution
```

Infrastructure files:

- `infra/bigquery.sql` — fresh governed schema + vector index
- `infra/migrate_nexus_acl.sql` — upgrade existing corpus
- `infra/deploy.sh` — Cloud Run/IAP reference deployment

The deploy script intentionally defaults `ACCESS_PROFILES_JSON={}` in IAP mode, which means enterprise users receive only public-corpus employee access until trusted directory entitlements are configured. This is a secure default, not an automatic privilege grant.

---

# API surface

### Knowledge

- `GET /health`
- `POST /api/auth/login` — local demo only
- `POST /api/chat`
- `GET /api/conversations/{conversation_id}`
- `GET /api/documents`

### Knowledge administration

- `POST /api/ingest` — knowledge admin
- `POST /api/evaluate` — knowledge admin
- `GET /api/audit/verify` — knowledge admin

### Controlled actions

- `POST /api/actions/request`
- `GET /api/actions/{action_id}`
- `POST /api/actions/{action_id}/approve` — knowledge admin
- `POST /api/actions/{action_id}/execute` — knowledge admin

---

# Repository structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   │   ├── access.py
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── services/
│   │   │   ├── rag.py
│   │   │   ├── reranking.py
│   │   │   ├── evaluation.py
│   │   │   ├── audit.py
│   │   │   ├── actions.py
│   │   │   └── actions_bigquery.py
│   │   └── stores/
│   │       ├── local.py
│   │       └── bigquery.py
│   └── tests/
├── frontend/
├── evaluation/
├── sample_data/
├── docs/
├── infra/
└── docker-compose.yml
```

---

# Interview-defensible engineering decisions

**Why ACL before retrieval?**  
Because post-filtering is too late if restricted evidence can already enter ranking, generation context, tracing, or caching.

**Why RRF followed by reranking?**  
Semantic and lexical scores are not directly comparable. RRF combines their rankings; the second stage adds query-specific ordering without redefining evidence confidence.

**Why keep grounding confidence separate from the rerank score?**  
Ranking and evidence sufficiency are different decisions. A ranking heuristic should not silently make weak evidence look grounded.

**Why deterministic orchestration rather than autonomous multi-agent behavior?**  
Policy systems benefit from constrained, auditable control flow: retrieve, inspect evidence, generate or abstain, then route side effects through explicit approval.

**Why approval-gated actions?**  
Knowledge access and side effects have different risk classes. The model can help formulate a request; it does not receive unilateral authority to execute it.

**Why idempotency?**  
Retries happen in distributed systems. Side-effect requests need stable duplicate protection so a transient network retry does not create multiple tickets or exceptions.

**Why a hash-chained audit log locally?**  
Persistence alone does not make audit history trustworthy. Chaining each event to the prior event makes later modification detectable during verification.

---

# Current limitations

- the bundled policy corpus is fictional and intentionally small
- production entitlements must come from a real identity/directory system rather than static JSON configuration
- the Google Cloud reference deployment must be validated against the target organization's residency, IAM, model-risk, logging, and retention requirements
- conversation history is process-local; a production customer should either make chat stateless or persist conversation state in a retention-controlled store
- the external action executor is intentionally a controlled demo handoff, not a fake live ServiceNow/HRIS integration
- local lexical retrieval is lightweight rather than a full production BM25 service
- BigQuery cloud retrieval currently uses vector candidates plus the NEXUS reranker; a managed lexical/hybrid backend can be added when production evaluation shows the need

---

# Further evaluation before real deployment

The next evidence—not missing core architecture—would be customer/environment specific:

- a larger 50–100+ bilingual golden set
- real document entitlement mappings
- external retrieval benchmarks
- adversarial prompt-injection/red-team cases
- ANN recall/latency/cost evaluation at realistic corpus size
- cloud load testing
- enterprise identity integration
- approved live workflow adapters
- customer-specific monitoring, retention, and data-residency controls

---

# Documentation

- `docs/NEXUS_ARCHITECTURE.md`
- `docs/NEXUS_SECURITY_MODEL.md`
- `docs/NEXUS_ACTIONS.md`
- `docs/NEXUS_EVALUATION.md`
- `docs/NEXUS_RUNBOOK.md`

---

## Portfolio summary

NEXUS demonstrates the full enterprise GenAI lifecycle: **bilingual RAG, authorization-aware retrieval, hybrid ranking, reranking, evidence-based abstention, grounded generation, citation integrity, secure ingestion, auditability, controlled actions, human approval, durable cloud state, CI quality gates, Docker, FastAPI, Next.js, Gemini, BigQuery Vector Search, Cloud Run, and IAP.**

The central design principle is simple: **an enterprise AI system should never see evidence the user is not allowed to retrieve, and it should never perform an action merely because a model suggested it.**
