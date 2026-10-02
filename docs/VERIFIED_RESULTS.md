# Verified results

This document records the strongest repository-backed validation evidence for NEXUS.

## Current reference validation

**GitHub Actions:** NEXUS CI — run #74  
**Date:** 2 October 2026  
**Validated commit:** 83328e2eb599276b655d1d197b361308f7011c87  
**Workflow conclusion:** success

### Backend, security and assurance tests

**36/36 tests passed** in CI.

The suite now includes the original backend/security coverage plus two deliberate adversarial assurance rounds covering authorization, approval provenance, segregation of duties, replay/idempotency semantics, audit integrity, event-quality requirements and exception monitoring.

### Adversarial testing and remediation

The assurance work was intentionally run red before remediation rather than reporting only green tests:

- **Run #65:** 12 adversarial test cases failed while 18 existing tests passed.
- The first remediation round addressed idempotency-key conflicts, requester execution, non-finite input, blank idempotency keys and multiple audit-analytics blind spots.
- **Run #68:** 30/30 tests passed after first-round remediation.
- **Run #69:** a second challenge round produced 6 failing adversarial cases while 30 tests passed.
- The second remediation round addressed audit-tail truncation, approval-provenance tampering and blank required audit-event fields.
- **Run #72:** 36/36 tests passed after second-round remediation.
- **Run #74:** 36/36 tests remained green after the executable assurance review was expanded.

The failures are grouped into **12 distinct documented development/control findings** in assurance/adversarial_findings.json. These are findings against a self-built fictional system, not independent client-audit findings.

### Executable Technology Assurance Control Review

Run #74 executed a separate deterministic assurance review:

| Result | Value |
|---|---:|
| controls tested | 20 |
| controls passed | 20 |
| controls failed | 0 |
| overall result | passed |

The 20 controls cover logical access, entitlement behavior, execution-before-approval, administrator authorization, self-approval prevention, idempotency/replay protection, action allowlisting, changed-request idempotency conflicts, malformed numeric input, requester/executor segregation, valid state transitions, audit-chain integrity, exception analytics, stored-row tampering, tail-truncation detection, required audit fields, approval-provenance integrity, change-management quality gates and AI-assurance evaluation coverage.

### Controlled RAG evaluation

The same run retained the eight-case bilingual regression gate:

| Metric | Result |
|---|---:|
| total_cases | 8 |
| retrieval_hit_at_k | 1.0 |
| citation_rate | 1.0 |
| citation_source_integrity_rate | 1.0 |
| grounding_decision_accuracy | 1.0 |
| language_match_rate | 1.0 |
| grounded_keyword_coverage | 1.0 |
| avg_latency_ms | 2.125 |

### Other CI gates

- frontend production build — success;
- deployment-script syntax validation — success;
- Docker Compose configuration validation — success;
- assurance-evidence artifact upload — success.

## What these results establish

They establish reproducible control-design and negative-testing evidence on the self-built fictional NEXUS environment. More importantly than the final pass rate, the CI history shows that adversarial tests exposed control weaknesses, those weaknesses were documented and remediated, and the expanded regression suite was rerun successfully.

## What these results do **not** establish

They are not evidence of production operating effectiveness over a defined audit period, an independent audit opinion, SOC 1/SOC 2/SOX/ISAE 3402 compliance, real ERP/ICFR audit coverage, client deployment, production IAM lifecycle effectiveness, security against all attacks, or business ROI.

A real engagement would still require independent evidence, a defined audit population and period, sampling, control owners, reviewer sign-off, production identity/change records and customer-specific criteria.
