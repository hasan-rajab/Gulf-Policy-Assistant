# NEXUS Technology Assurance Review

## Purpose

This document turns NEXUS into a reproducible technology-assurance case study rather than only an engineering portfolio project.

The review demonstrates how to move from:

**system walkthrough -> risk identification -> control objective -> control design -> test procedure -> evidence -> exception analysis -> conclusion**

It is intentionally written in assurance language while preserving the repository's claims boundary.

> **Claims boundary:** this is a self-contained portfolio control review of a fictional demo system. It is not an independent audit, SOC report, SOX opinion, ISAE 3402 engagement, regulatory certification, or evidence of production operating effectiveness over a real client population.

The machine-readable risk/control matrix is in assurance/control_matrix.json. The executable review is in backend/app/services/assurance.py.

---

## 1. System walkthrough

### In-scope process

Authenticated identity flows to server-side role/department entitlement resolution, then to an ACL-scoped candidate corpus, semantic and lexical retrieval, deterministic reranking, and an evidence-sufficiency decision. Sufficient evidence produces a grounded response with citations; insufficient evidence produces abstention/escalation. Both paths produce structured audit evidence.

The side-effect plane is separate: a user action request passes an allowlist and payload validation, enters pending_approval, requires an authorized independent approver, moves to approved, then permits guarded execution and records an audit event.

### In-scope components

- backend/app/core/access.py — authorization model
- backend/app/core/security.py — identity resolution and server-side entitlement lookup
- backend/app/stores/local.py and backend/app/stores/bigquery.py — retrieval authorization boundary
- backend/app/services/rag.py — grounding and audit behavior
- backend/app/services/actions.py — approval-gated action workflow
- backend/app/services/audit.py — tamper-evident audit trail
- backend/app/services/audit_analytics.py — deterministic control-exception analytics
- backend/app/services/evaluation.py — AI evaluation logic
- .github/workflows/ci.yml — automated change-quality gates

### Out of scope

- real enterprise IAM joiner/mover/leaver administration
- production ERP or financial-reporting systems
- live HR/IT workflow connectors
- independent auditor testing
- production SIEM/retention configuration
- production key-management and secrets lifecycle
- production population sampling across a defined audit period
- regulatory or contractual assurance opinions

---

## 2. Risk assessment

The assurance scope focuses on risks that materially affect confidentiality, authorization, processing integrity, AI reliability, and traceability.

| Risk | Inherent concern | Primary control response |
|---|---|---|
| Unauthorized retrieval | restricted enterprise information is exposed | ACL filtering before candidate scoring |
| Untrusted client claims | caller grants itself privileged roles | server-side entitlement resolution |
| Unapproved side effect | model/caller causes an enterprise action without human authority | approval-gated state machine |
| Privileged self-approval | requester bypasses independent authorization | four-eyes control |
| Replay/duplicate action | repeated request creates duplicate side effects | idempotency key |
| Arbitrary tool execution | model invokes unknown or high-risk capability | fixed allowlist + schema validation |
| Audit tampering | control history is modified without detection | SHA-256 hash chain |
| Hidden workflow exception | bad approval/execution sequence is not surfaced | deterministic audit analytics |
| Unsupported AI answer | fluent output is treated as evidence | evidence threshold + abstention |
| Citation mismatch | answer cites evidence not actually returned | citation-source integrity evaluation |
| Unsafe change | code change bypasses quality controls | CI test/evaluation/build/deploy gates |

See docs/AI_RISK_REGISTER.md for the broader enterprise AI risk register.

---

## 3. Design-effectiveness assessment

Design effectiveness asks:

> **If the control operates exactly as designed, is it capable of addressing the stated risk?**

NEXUS demonstrates this assessment explicitly.

### Example: GITC-AC-01 — pre-retrieval authorization

**Risk:** an unauthorized employee retrieves restricted content.

**Control:** LocalVectorStore._authorized_chunks() reduces the searchable corpus using the identity-derived AccessContext before semantic or lexical scoring.

**Design assessment:** the design directly addresses the risk because unauthorized chunks are not eligible for candidate scoring. This is stronger than retrieving restricted text and filtering it only after ranking or generation.

### Example: ITAC-ACT-01 — execution approval gate

**Risk:** a side-effecting enterprise action executes without explicit human authorization.

**Control:** action requests persist in pending_approval; execute() rejects any action not already in approved.

**Design assessment:** the design separates recommendation/request from execution authority and uses a deterministic state transition rather than model judgment.

### Example: ITAC-ACT-03 — segregation of duties

**Risk:** a privileged requester authorizes their own action.

**Control:** the requester is prohibited from approving the same action even when the requester has an administrator role.

**Design assessment:** this implements a four-eyes pattern and removes a direct self-approval path.

### Example: GITC-OPS-02 — audit tamper detection

**Risk:** an event record is changed after the fact.

**Control:** each local audit event stores the previous event hash and its own calculated hash.

**Design assessment:** changing a historical row breaks chain verification. This is tamper-evident, not immutable storage; production retention still requires an independently protected logging platform.

---

## 4. Operating-effectiveness testing

Operating effectiveness asks:

> **Did the control actually operate as designed for the transactions or population tested?**

NEXUS now includes an executable assurance review.

Run:

    PYTHONPATH=backend python backend/scripts/run_assurance_review.py --output assurance-report.json

The script builds disposable local stores and executes the following tests:

1. unauthorized restricted-document retrieval
2. authorized HR retrieval
3. execution-before-approval denial
4. non-admin approval denial
5. administrator self-approval denial
6. idempotency/replay protection
7. arbitrary action rejection
8. normal approved action lifecycle
9. audit-chain verification
10. audit exception analytics
11. controlled audit-row tampering
12. CI gate inspection
13. AI evaluation-set coverage inspection

The JSON report records each control ID, objective, pass/fail result, evidence description, and any exception.

### Important sampling limitation

Automated tests provide strong reproducible evidence for the code paths exercised, but they are **not equivalent to testing a production population over a financial or operational period**.

For a real engagement, operating-effectiveness testing would define the audit period, population, sampling methodology, evidence ownership, exception criteria, re-performance requirements, and reviewer sign-off.

---

## 5. Audit analytics

backend/app/services/audit_analytics.py performs explainable control analytics over structured events.

Current exception tests include:

- **SELF_APPROVAL** — requester and approver are the same principal
- **EXECUTION_WITHOUT_RECORDED_APPROVAL** — an execution event has no prior approval event in the analyzed sequence
- **REPEATED_DENIED_LOGIN** — repeated denied authentication events meet the configured threshold

These analytics are deliberately deterministic so the reviewer can explain exactly why an exception was raised.

They are portfolio assurance evidence, not a replacement for a production SIEM, UEBA platform, or continuous-controls-monitoring program.

---

## 6. Workpaper structure

A reviewer can trace each tested control using the following fields:

- control ID
- process/domain
- risk
- control objective
- control implementation
- test procedure
- evidence source
- result
- exception
- claims/period limitation

See assurance/control_matrix.json and docs/ASSURANCE_WORKPAPERS.md.

---

## 7. Deficiency and remediation logic

NEXUS distinguishes a control failure from a portfolio scope limitation.

### Control exception

Example: an execution event appears without a prior approval event.

Response: flag the exception, identify the affected action/resource, determine whether the state machine or audit event was bypassed, contain the workflow, remediate the control, and re-perform the test.

### Scope limitation / production gap

Example: the local JWT/IAP reference architecture does not demonstrate a real customer's joiner/mover/leaver process.

Response: do not call the control ineffective based on missing production evidence; state that production IAM operating effectiveness is outside the demo scope and define the evidence required in a real engagement.

---

## 8. Residual gaps that cannot be truthfully eliminated inside a demo repository

The repository now demonstrates the methodology and technical control evidence, but these items require a real organization or engagement:

1. **production IAM lifecycle evidence** — joiner/mover/leaver tickets, access reviews, directory evidence
2. **production change population** — approved change tickets, reviewer evidence, deployment history across an audit period
3. **real ERP/financial process scope** — SAP/Oracle transactions, interfaces, automated controls, financially significant reports
4. **formal SOC/SOX/ISAE assurance** — independent criteria, engagement period, sampling, reviewer sign-off, opinion/report
5. **real business-control ownership** — named process/control owners and remediation accountability
6. **production SIEM/retention** — immutable centralized log retention and alert operations

Those are deliberately presented as residual engagement requirements rather than fabricated experience.

---

## 9. Interview-ready explanation

A concise explanation of the assurance work is:

> NEXUS started as a governed RAG system, but I extended it into a technology-assurance case. I documented risks and controls, mapped GITC and application-control themes, implemented four-eyes approval, added deterministic audit analytics, and built an executable review that tests logical access, approval state transitions, replay prevention, audit integrity, change-management gates, and AI evaluation coverage. I separate design effectiveness from operating effectiveness and explicitly state where a demo cannot substitute for production-period audit evidence.
