# NEXUS — Career Case Study

## One-line explanation

NEXUS is a governed Arabic/English enterprise RAG and technology-assurance case study where identity, retrieval authorization, evidence grounding, human approval, segregation of duties, auditability, and AI evaluation are designed as one control environment.

## 30-second recruiter version

I built NEXUS to solve the enterprise problem behind RAG: an LLM should only retrieve information an authenticated employee is allowed to see, and generated text should never become authority to execute a business action. NEXUS enforces document ACLs before retrieval scoring, uses grounded evidence and citations, abstains when evidence is insufficient, and puts enterprise actions behind allowlisted, approval-gated workflows. I then extended the project into a technology-assurance case with a risk/control matrix, GITC and application-control testing, four-eyes approval, audit analytics, workpapers, and an executable 20-control assurance review.

## 90-second interview version

The system started as a bilingual policy assistant, but I redesigned it around enterprise authorization. The critical rule is that access control happens before semantic or lexical scoring. In local mode, unauthorized chunks are removed from the candidate corpus before retrieval. The BigQuery path carries roles, departments, and visibility metadata into the vector-search base query.

After retrieval, NEXUS fuses semantic and lexical candidates, applies deterministic reranking, and uses a separate evidence threshold for grounding. If approved evidence is not strong enough, it abstains instead of improvising an answer. Citation-to-source integrity checks verify that generated citations map to evidence actually returned by the retrieval path.

For side effects, I separated the action plane from the answer plane. Only allowlisted actions with strict schemas can be requested. They move through `pending_approval -> approved -> executed`, use idempotency, and now enforce a four-eyes rule: the requester cannot approve their own action, even if privileged. Denied approval and execution attempts are also recorded as structured audit events.

I then treated the system as a technology-assurance subject. I documented risks and control objectives, separated design effectiveness from operating effectiveness, created workpapers, mapped GITC and IT application-control themes, and wrote deterministic analytics for self-approval, execution-without-approval, and repeated denied-login exceptions. The CI pipeline executes an assurance review rather than merely documenting the controls.

I then added a deterministic 1,000-case escalating adversarial campaign. Its first run deliberately went red: **300/1,000 cases failed**, exposing three additional weaknesses around Unicode control characters and non-finite audit evidence. After remediation and targeted regression tests, NEXUS CI run #82 validated **47/47 regression tests**, **1,000/1,000 campaign cases**, the controlled eight-case RAG gate, and a separate **20/20 technology-assurance control review**.

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
  -> independent authorized approver
  -> no self-approval / four-eyes
  -> guarded execution
  -> audited handoff reference

assurance layer:
risk
  -> control objective
  -> design assessment
  -> test procedure
  -> evidence
  -> exception analysis
  -> conclusion
```

## Technology-assurance problems I can defend

### 1. Retrieval-time authorization

**Risk:** restricted text can leak into candidate generation, traces, caches, reranking, or model context if filtering happens too late.

**Control:** scope the corpus to authorized chunks before semantic or lexical scoring.

**Testing:** negative test as an unauthorized operations user plus positive test as an authorized HR principal.

### 2. Design effectiveness vs operating effectiveness

**Design effectiveness:** if the control operates as designed, is it capable of addressing the risk?

**Operating effectiveness:** did it actually operate as designed for the transactions/population tested?

NEXUS documents the design and then re-performs controls through deterministic tests. The project explicitly does not turn a demo test population into a production-period audit conclusion.

### 3. LLM output vs action authority

**Risk:** generated output becomes implicit authorization to mutate an enterprise system.

**Control:** separate the side-effect plane, enforce allowlists/schemas, require approval, and use persisted state transitions.

**Testing:** attempt execution before approval and confirm deterministic denial.

### 4. Segregation of duties

**Risk:** a privileged requester approves their own action.

**Control:** requester identity cannot equal approver identity.

**Testing:** create a request as an administrator and deliberately attempt administrator self-approval; the request is denied and the denial is audited.

### 5. Processing integrity / replay

**Risk:** repeated requests create duplicate side effects.

**Control:** requester + idempotency key identifies the existing request.

**Testing:** submit the same request twice and confirm both references resolve to the same action.

### 6. Audit integrity

**Risk:** historical audit evidence is changed without detection.

**Control:** local events use a SHA-256 hash chain.

**Testing:** verify a valid chain, modify a stored event in a disposable database, then confirm verification fails.

### 7. Continuous control analytics

**Risk:** invalid approval/execution sequences exist without reviewer visibility.

**Control:** deterministic audit analytics identify self-approval, execution without recorded approval, and repeated denied logins.

**Testing:** run both clean and intentionally invalid event sequences and inspect exact exception types.

### 8. Change management

**Risk:** code changes bypass quality/security assurance.

**Control:** GitHub Actions gates backend/security tests, strict AI evaluation, the technology-assurance review, frontend build, and deployment-configuration checks.

**Limitation:** CODEOWNERS and a control-impact PR template are repository artifacts; branch-protection/reviewer enforcement is a separate GitHub setting and is not claimed as active unless configured.

### 9. AI assurance

**Risk:** the system answers unsupported questions, loses citation integrity, or follows adversarial instructions.

**Control:** evidence gating, abstention, citation checks, bilingual evaluation, and adversarial regression testing.

**Evidence:** run #82 retained all eight controlled evaluation metrics at 1.0; average deterministic local evaluation latency was 1.25 ms.

## Evidence

- Arabic/English hybrid RAG
- semantic + lexical retrieval and reciprocal-rank fusion
- deterministic reranking and evidence sufficiency
- retrieval-time role/department ACLs
- server-side entitlement resolution
- grounded abstention and citation-to-source integrity
- allowlisted and schema-validated controlled actions
- four-eyes segregation of duties
- idempotency / replay prevention
- denied approval/execution audit evidence
- tamper-evident SQLite audit chain
- deterministic audit exception analytics
- SQLite + BigQuery persistence paths
- risk/control matrix and assurance workpapers
- design-effectiveness and operating-effectiveness methodology
- GITC / ITAC / AI-assurance relevance mapping
- FastAPI + Next.js
- Docker + GitHub Actions
- **Earlier adversarial rounds exposed 18 failing test cases across 12 documented findings before remediation**
- **A later 1,000-case escalating campaign initially produced 300 failures across 3 additional finding classes**
- **47/47 regression tests and 1,000/1,000 campaign cases passed in CI run #82 after remediation**
- **20/20 executable assurance controls passed**
- **8/8 controlled RAG evaluation cases passed their regression gate**

## CV-ready bullets

- Engineered a governed Arabic/English enterprise RAG platform with retrieval-time authorization, hybrid retrieval, deterministic reranking, grounded abstention, and citation-to-source integrity controls.
- Designed and tested GITC/IT application-control patterns across logical access, approval workflows, segregation of duties, replay prevention, audit integrity, change-management gates, and AI assurance.
- Implemented four-eyes approval, idempotent allowlisted actions, tamper-evident audit logging, and deterministic exception analytics for self-approval and unauthorized workflow transitions.
- Built a **1,000-case escalating adversarial assurance campaign**; the first run exposed **300 failing cases** across three new control-evidence weaknesses, which were remediated before rerunning **1,000/1,000 cases**, **47/47 regression tests**, and a **20/20 executable assurance control review** successfully.

## Claims boundary

NEXUS demonstrates production-oriented architecture, control design, and reproducible portfolio assurance testing on a fictional corpus. It is not a claim of client employment, production deployment, formal SOC/SOX/ISAE assurance, ERP/ICFR audit experience, or operating effectiveness across a real audit period.
