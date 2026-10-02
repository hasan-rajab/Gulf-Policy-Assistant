# NEXUS Framework Relevance Map

NEXUS is not presented as certified or compliant with any assurance framework. This document maps demonstrated control patterns to common technology-assurance concepts so the project can be discussed accurately in audit/risk conversations.

## Mapping principles

- **GITC** mappings describe general IT control categories such as logical access, change management, and IT operations.
- **ITAC** mappings describe application-level authorization, validation, processing, and approval controls.
- **SOX / ICFR** references are conditional: a technology control becomes relevant to SOX only when it supports financially significant systems/processes in scope.
- **SOC 1 / ISAE 3402** references are conditional on a service organization providing controls relevant to user entities' financial reporting.
- **SOC 2** references are high-level trust-service themes, not an assertion that NEXUS has undergone a SOC 2 examination.
- **COBIT/COSO** references describe governance/control themes rather than formal implementation.
- **AI assurance** references describe governance, validation, traceability, and human-oversight patterns.

## Control relevance

| NEXUS capability | Assurance concept | Why it matters |
|---|---|---|
| Server-side entitlement resolution | GITC logical access | client-supplied privilege claims do not determine access |
| ACL filtering before retrieval scoring | GITC logical access / application authorization | restricted data is removed before ranking/model context |
| Admin-only ingestion/evaluation | privileged access | higher-risk administrative operations are restricted |
| Fixed action allowlist | ITAC authorized processing | unregistered tools/actions cannot be invoked |
| Strict payload schema | ITAC input validation | unknown fields and invalid values are rejected |
| Approval state machine | ITAC authorization | execution cannot occur from pending state |
| Four-eyes approval | segregation of duties | requester cannot approve own action |
| Idempotency | ITAC processing integrity | repeated requests do not create duplicate actions |
| Hash-chained audit | GITC operations / monitoring | historical record changes become detectable |
| Audit analytics | monitoring / continuous controls testing | known exception patterns are surfaced deterministically |
| CI backend/security tests | GITC change management | changes are regression-tested |
| Strict RAG evaluation gate | AI assurance | grounding/citation/abstention behavior is measured |
| Human approval before side effects | responsible AI / human oversight | model output does not become execution authority |

## SOX / ICFR discussion

A useful distinction in interviews is:

**NEXUS demonstrates control mechanics that resemble GITCs and application controls; it does not demonstrate SOX scope.**

For example, logical-access and change-management controls could be relevant in a SOX engagement if the application supported financial reporting. NEXUS has no real general ledger, financial close, revenue, purchasing, payroll, or financially significant ERP population, so the repository does not claim ICFR operating effectiveness.

## SOC 1 / ISAE 3402 discussion

If NEXUS were operated as a service that affected customers' financial-reporting controls, authorization, change management, processing controls, and monitoring could become relevant to a SOC 1 / ISAE 3402-style control environment.

The demo does not establish that scope, service commitment, audit period, test population, or independent assurance report.

## SOC 2 discussion

The most directly relevant themes are:

- logical access and authorization
- change control
- security-event traceability
- processing integrity for approval-gated actions
- confidentiality boundaries around restricted knowledge

A real SOC 2 examination would require defined system boundaries, service commitments, criteria mapping, evidence across an examination period, and independent testing.

## COBIT / COSO discussion

NEXUS supports conversations about:

- governance and risk ownership
- access/security management
- controlled change
- monitoring and exception handling
- separation of duties
- control design and evidence

The repository intentionally avoids claiming COBIT implementation maturity or COSO effectiveness because those conclusions require organizational processes beyond application source code.

## AI assurance discussion

The strongest distinctive assurance evidence in NEXUS is the combination of:

- authorization before retrieval
- evidence sufficiency before answering
- citation-to-source integrity checks
- safe abstention
- adversarial evaluation
- human approval before side effects
- structured audit evidence
- deterministic exception analytics

This makes NEXUS useful for discussing how traditional technology assurance extends into AI-enabled systems without treating the model itself as the control owner.
