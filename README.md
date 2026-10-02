# NEXUS Enterprise AI

**A governed bilingual enterprise AI reference architecture for trusted knowledge access and approval-gated workflows.**

NEXUS is built around a business problem, not a model:

> **How can an enterprise use generative AI for internal knowledge and workflow assistance without weakening access control, evidence quality, auditability, or human authority?**

The recommended operating model is intentionally phased:

**governed read-only RAG → department copilot → approval-gated actions**

This repository contains the working reference implementation behind that recommendation.

> **Scope:** NEXUS uses a fictional GCC enterprise and a controlled demo corpus. Business assumptions are illustrative. Repository-backed validation results are reported separately from production claims.

---

## Executive view

| Business question | NEXUS answer |
|---|---|
| How do employees find policy information faster? | Bilingual hybrid RAG with grounded answers and citations |
| How do we prevent unauthorized retrieval? | Role/department ACLs are enforced **before** semantic or lexical scoring |
| What happens when evidence is weak? | The system abstains or escalates instead of improvising |
| Can the model take enterprise actions? | Only through allowlisted, schema-validated, approval-gated workflows |
| Can decisions be reconstructed later? | Requests, retrieval, approvals and execution paths are auditable |
| How should this be rolled out? | Start read-only, validate quality/value, then increase autonomy gradually |

### Consulting deliverables

- [Executive case study](docs/EXECUTIVE_CASE_STUDY.md)
- [Illustrative business case](docs/ILLUSTRATIVE_BUSINESS_CASE.md)
- [AI risk register](docs/AI_RISK_REGISTER.md)
- [Implementation roadmap](docs/IMPLEMENTATION_ROADMAP.md)
- [Verified results](docs/VERIFIED_RESULTS.md)
- [Career/interview case](docs/CAREER_CASE_STUDY.md)
- [Technology assurance review](docs/TECHNOLOGY_ASSURANCE_REVIEW.md)
- [Assurance workpapers](docs/ASSURANCE_WORKPAPERS.md)
- [Framework relevance map](docs/FRAMEWORK_RELEVANCE.md)
- [Machine-readable risk/control matrix](assurance/control_matrix.json)

---

## Business value

NEXUS is designed to address four enterprise value levers:

1. **Employee productivity** — reduce time spent searching and interpreting fragmented policy content.
2. **Risk control** — keep restricted evidence outside unauthorized retrieval paths.
3. **Decision quality** — require grounded evidence and traceable citations before answering.
4. **Controlled automation** — separate AI-generated suggestions from permission to execute side effects.

The included [illustrative business case](docs/ILLUSTRATIVE_BUSINESS_CASE.md) shows how a consultant could quantify time saved, adoption, run cost, payback and sensitivity **without presenting fictional assumptions as realized client savings**.

---

## Architecture

```text
Enterprise identity
      ↓
Server-side role / department entitlements
      ↓
Authorized corpus scope
      ↓
Semantic retrieval + lexical retrieval
      ↓
Reciprocal Rank Fusion
      ↓
Deterministic reranking
      ↓
Evidence sufficiency gate
      ├── sufficient → grounded answer + citations
      └── insufficient → abstain / escalate
      ↓
Audit event

Separate side-effect plane:

Action request
      ↓
Allowlist + strict payload schema
      ↓
pending_approval
      ↓
authorized human approval
      ↓
approved
      ↓
guarded execution
      ↓
audited handoff / result
```

### Critical design decision: authorization before retrieval

NEXUS scopes the searchable corpus to authorized chunks **before** semantic or lexical scoring.

That matters because post-retrieval filtering can be too late: restricted text may already have entered candidate generation, reranking, traces, caches, citations, or model context.

Local mode applies ACLs before cosine/lexical scoring. The BigQuery path carries access metadata into the vector-search base query.

---

## Verified results

**Reference validation:** NEXUS CI run #59  
**Date:** 1 September 2026  
**Pinned commit:** `b7da2a70ac37c43f1d270e1a52c16fb060084f1d`

### Backend / security
- **14/14 tests passed**

### Controlled RAG evaluation
- **8 cases**
- retrieval hit@k: **1.000**
- citation rate: **1.000**
- citation-to-source integrity: **1.000**
- grounding-decision accuracy: **1.000**
- language-match rate: **1.000**
- grounded keyword coverage: **1.000**
- average deterministic local evaluation latency: **2.0 ms**

The same CI run also completed the frontend production build and deployment-configuration validation successfully.

> These metrics validate expected behavior on the bundled fictional corpus. They are **not** claims of production-bank accuracy, safety, security, scale, or latency.

---

## Governance and security controls

### Retrieval and data access
- server-side user-role and department resolution
- retrieval-time document ACL enforcement
- restricted chunks removed before ranking
- document visibility and ACL metadata persisted with chunks
- client-supplied role/department claims ignored

### Grounding
- semantic + lexical retrieval
- Reciprocal Rank Fusion
- deterministic reranking
- evidence thresholding
- safe abstention
- inline citations
- citation-to-returned-source integrity checks

### Controlled actions
- fixed action allowlist
- strict payload schemas
- idempotent requests
- persisted `pending_approval → approved → executed` state machine
- four-eyes segregation of duties: requester cannot approve their own action
- guarded transitions to prevent approval bypass/replay
- denied approval/execution attempts written to the audit trail
- portfolio-safe handoff rather than pretending a live HR/IT integration exists

### Auditability
- local SQLite audit trail
- SHA-256 hash-chain verification
- BigQuery audit-event production path
- request IDs and structured application logs
- deterministic audit analytics for self-approval, execution-without-approval, and repeated denied-login exceptions

---

## Technology assurance evidence

NEXUS now includes an executable control-review layer designed around technology-assurance methodology rather than résumé wording alone.

It covers:

- system/process walkthrough and defined scope;
- risk and control matrix;
- GITC logical-access, change-management, operations and monitoring themes;
- IT application controls for authorization, schema validation, approval and replay prevention;
- four-eyes segregation of duties;
- design-effectiveness and operating-effectiveness test logic;
- audit workpapers and exception criteria;
- deterministic audit analytics;
- AI-assurance evaluation coverage;
- cautious SOX/ICFR, SOC 1/ISAE 3402, SOC 2, COBIT/COSO relevance mapping without claiming certification or formal assurance.

Run the local assurance review with:

    PYTHONPATH=backend python backend/scripts/run_assurance_review.py --output assurance-report.json

CI also runs this review and uploads the generated JSON evidence report as a workflow artifact.

See [Technology assurance review](docs/TECHNOLOGY_ASSURANCE_REVIEW.md).

---

## Technology

**Backend:** Python · FastAPI  
**Frontend:** Next.js  
**Retrieval:** semantic search · lexical search · RRF · deterministic reranking  
**Persistence:** SQLite local path · BigQuery production reference path  
**Cloud reference:** Google Cloud · Cloud Run · BigQuery Vector Search · Gemini · IAP  
**Delivery:** Docker · GitHub Actions

---

## Pilot approach

A real enterprise pilot should start narrow:

- one policy domain;
- clearly defined employee groups;
- 50–100 representative bilingual golden questions;
- explicit access-control tests;
- baseline time-on-task measurement;
- quality, latency and escalation thresholds;
- adoption and user-feedback measurement.

Only after the read-only capability proves quality and value should side-effecting workflows be introduced.

---

## Run locally

See the repository setup and environment files for local execution. The project includes Docker-based local deployment plus separate local/managed infrastructure paths.

Useful supporting documentation:

- [Architecture](docs/NEXUS_ARCHITECTURE.md)
- [Security model](docs/NEXUS_SECURITY_MODEL.md)
- [Evaluation](docs/NEXUS_EVALUATION.md)
- [Runbook](docs/NEXUS_RUNBOOK.md)
- [Release checklist](docs/NEXUS_RELEASE_CHECKLIST.md)

---

## Claims boundary

NEXUS demonstrates a **production-oriented architecture and control model**, not a production customer deployment.

The strongest claims in this repository are the ones that can be reproduced from source, tests, evaluation data and CI. Fictional customer context, business assumptions and future production architecture are labeled accordingly.
