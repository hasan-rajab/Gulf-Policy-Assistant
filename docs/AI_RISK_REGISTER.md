# NEXUS — AI Risk Register

## Purpose

A consulting-grade AI recommendation should make risks explicit rather than hiding them inside architecture language.

The register below maps major enterprise GenAI risks to controls already demonstrated in NEXUS and to controls that would still be required for a real production deployment.

| Risk | Business consequence | Inherent severity | NEXUS control / design response | Production follow-up |
|---|---|---|---|---|
| Unauthorized document retrieval | Confidential data exposure | Critical | ACL filtering before semantic/lexical scoring; server-side entitlements | Integrate enterprise IAM/SSO and authoritative group lifecycle |
| Hallucinated policy answer | Incorrect employee action / compliance failure | High | Evidence sufficiency gate, grounded generation, safe abstention | Larger golden set, human review thresholds, continuous evaluation |
| Citation mismatch | False confidence and poor auditability | High | Citation-to-returned-source integrity checks | Page/section-level provenance and document version tracking |
| Prompt injection | Policy bypass or unsafe model behavior | High | Controlled orchestration, evidence boundaries, adversarial regression case | Dedicated red-team program, content isolation, vendor/model hardening |
| Excessive agent authority | Unauthorized side effect | Critical | Separate action plane, allowlist, schemas, human approval | Fine-grained tool entitlements and enterprise workflow adapters |
| Privileged self-approval | Requester bypasses independent authorization | High | Four-eyes rule blocks requester from approving own action; denial is audited | Enterprise SoD matrix, compensating controls, periodic privileged-access review |
| Duplicate/replayed action | Repeated side effect | High | Idempotency and guarded workflow state transitions | Distributed locking / transactional integration where required |
| Audit tampering | Inability to reconstruct decisions | High | SHA-256 hash-chained local audit trail | Centralized immutable retention / SIEM integration |
| Hidden workflow exception | Invalid approval/execution sequence goes unnoticed | High | Deterministic audit analytics for self-approval, execution without recorded approval, and repeated denied logins | SIEM/CCM integration, alert ownership, investigation SLAs |
| Stale policy content | Correctly grounded but outdated answer | High | Source provenance and explicit ingestion pipeline | Document-owner SLAs, version/expiry metadata, freshness monitoring |
| Weak bilingual retrieval | Poor Arabic or English service quality | Medium–High | Bilingual evaluation and language matching | Broader Arabic varieties and domain-specific evaluation |
| Overconfidence from small eval set | False production-readiness conclusion | High | Explicit claims boundary; deterministic controlled suite only | 50–100+ representative pilot questions, red-team and live shadow testing |
| Sensitive query logging | Privacy / confidentiality exposure | High | Query represented by SHA-256 in compliance audit rather than copied verbatim | Formal retention policy, DLP, secure telemetry design |
| Model/vendor dependency | Availability, cost, or policy change | Medium | Architecture separates orchestration from core controls | Model routing, fallback strategy, commercial/exit planning |
| Data residency mismatch | Regulatory/compliance issue | High | Deployment architecture acknowledges managed production path | Confirm jurisdiction, region, residency, encryption, contractual controls |

---

## Risk treatment philosophy

NEXUS follows three principles:

### 1. Controls belong before the model where possible
Authorization is enforced before retrieval rather than asking the model to respect access rights.

### 2. Confidence is not authority
A model may produce a highly confident answer, but it does not gain permission to execute an enterprise action.

### 3. Failure should be explicit
When evidence is insufficient, abstention and escalation are safer than improvisation.

---

## Suggested pilot go/no-go gates

A real deployment should define numeric thresholds with the client. Example categories:

- retrieval recall;
- grounded-answer accuracy;
- citation integrity;
- unsupported-question handling;
- unauthorized-retrieval prevention;
- bilingual performance;
- latency;
- escalation rate;
- user adoption.

No enterprise-wide rollout should be recommended solely because a demo appears convincing.
