# NEXUS — Career Case Study

## One-line explanation

NEXUS is a governed Arabic/English enterprise RAG system where identity, retrieval authorization, evidence grounding, action approval, and audit are designed as one security boundary.

## 30-second recruiter version

I built NEXUS to solve the enterprise problem behind RAG: an LLM should only retrieve information the authenticated employee is allowed to see and should never treat generated text as permission to execute a business action. NEXUS enforces document ACLs before retrieval scoring, uses hybrid retrieval and reranking, abstains when evidence is insufficient, audits access and decisions, and puts enterprise actions behind an approval-gated state machine.

## 90-second interview version

The system started as a bilingual policy assistant, but I redesigned it around enterprise authorization. The critical rule is that access control happens before semantic or lexical scoring. In local mode, unauthorized chunks are removed from the candidate corpus before retrieval. The BigQuery path carries roles, departments, and visibility metadata into the vector-search base query.

After retrieval, NEXUS fuses semantic and lexical candidates, applies deterministic reranking, and uses a separate evidence threshold for grounding. If approved evidence is not strong enough, it abstains instead of improvising an answer. I added citation-to-source integrity checks so generated citations must map to evidence that was actually returned.

For side effects, I separated the action plane from the answer plane. Only allowlisted actions with strict schemas can be requested. They move through `pending_approval -> approved -> executed`, require administrator approval, enforce idempotency, and are auditable. The portfolio executor produces a controlled handoff reference rather than pretending a real HR or IT integration exists.

The project also has a tamper-evident local audit chain, a BigQuery audit path, security regression tests, a deterministic bilingual RAG evaluation suite, Dockerized deployment, and CI gates for backend/security tests, frontend build, and deployment validation.

## Architecture story

```text
identity
  -> server-side roles/departments
  -> retrieval ACL scope
  -> semantic + lexical retrieval
  -> RRF candidates
  -> deterministic reranker
  -> evidence sufficiency gate
  -> grounded answer + citations OR abstention
  -> audit

separate action plane:
request
  -> allowlist + schema
  -> pending approval
  -> admin approval
  -> guarded execution
  -> audited handoff reference
```

## Engineering problems I can defend in an interview

### 1. Retrieval-time authorization
**Problem:** retrieving restricted chunks and filtering them afterward can leak sensitive text into context, reranking, traces, or caches.

**Fix:** scope the corpus to authorized chunks before semantic or lexical scoring.

**Lesson:** RAG authorization must be part of retrieval, not a presentation-layer filter.

### 2. Ranking vs grounding
**Problem:** the highest-ranked result is not automatically strong enough evidence to answer.

**Fix:** keep retrieval confidence separate from rerank ordering and apply an explicit evidence gate before generation.

**Lesson:** ranking quality and answer permission are different decisions.

### 3. LLM output vs action authority
**Problem:** a generated recommendation must not become authorization to mutate an enterprise system.

**Fix:** separate the side-effect plane, enforce an allowlist/schema, require approval, use idempotency, and audit every transition.

**Lesson:** tool use needs workflow governance, not just function calling.

### 4. Audit integrity
**Problem:** a local audit log is weak if rows can be changed without detection.

**Fix:** chain audit events using `previous_hash -> event_hash` and expose verification that detects stored-row tampering.

## Evidence

- Arabic/English hybrid RAG
- semantic + lexical retrieval
- reciprocal-rank fusion
- deterministic reranking
- retrieval-time ACLs
- server-side entitlement resolution
- grounded abstention
- citation-to-source integrity checks
- approval-gated controlled actions
- idempotency
- tamper-evident audit chain
- SQLite + BigQuery persistence paths
- FastAPI + Next.js
- Docker + GitHub Actions
- 14/14 backend/security tests and deterministic 8-case RAG regression suite on the fictional corpus

## Strong interview questions this project answers

**Why is post-retrieval filtering insufficient?**  
Because unauthorized text may already have entered candidate generation, scoring, logs, traces, caches, or model context. Pre-filtering shrinks the searchable corpus to information the principal is permitted to access.

**Why use deterministic reranking instead of another LLM?**  
For a compact governance-focused reference system, deterministic scoring keeps behavior inspectable, reproducible, inexpensive, and easy to regression-test. A learned reranker could replace it later without changing the authorization contract.

**How do you handle prompt injection?**  
The policy pipeline treats retrieved enterprise evidence and system rules as authoritative, rejects unsupported instructions, and includes adversarial cases in the regression evaluation. Prompt defenses are combined with authorization and grounding rather than treated as a prompt-only problem.

**What would change for a real enterprise?**  
Integrate enterprise IAM/SSO, managed secret storage, real document lifecycle/governance, production vector infrastructure, tenant isolation, centralized audit retention, DLP, red-team testing, and real approval/workflow adapters.

**Biggest limitation?**  
The bundled corpus is fictional and small. Perfect deterministic regression scores demonstrate expected behavior on that suite, not real enterprise accuracy or security guarantees.

## CV-ready bullets

- Engineered a governed Arabic/English enterprise RAG platform with hybrid retrieval, deterministic reranking, grounded abstention, and citation-to-source integrity checks.
- Implemented retrieval-time role/department ACL enforcement so restricted content is removed before semantic and lexical scoring.
- Built approval-gated, idempotent enterprise action workflows with strict tool schemas and tamper-evident audit logging.
- Added 14 backend/security regression tests, an 8-case bilingual RAG evaluation gate, Dockerized deployment, and CI validation for backend, frontend, and infrastructure paths.

## Claims boundary

The evaluation uses a deterministic fictional policy corpus. NEXUS demonstrates production-oriented architecture and control design; it is not a claim of deployment inside a real enterprise or of autonomous production tool execution.
