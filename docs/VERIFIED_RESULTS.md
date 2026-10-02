# Verified results

This document records the strongest repository-backed validation evidence for NEXUS.

## Current reference validation

**GitHub Actions:** NEXUS CI — run #82  
**Date:** 2 October 2026  
**Validated commit:** f0175250efb421ddc1151a118c1f35a3c20b85ec  
**Workflow conclusion:** success

### Backend, security and assurance tests

**47/47 regression tests passed** in CI.

The suite now includes the original backend/security coverage, two earlier adversarial assurance rounds, and targeted regression tests for the defects exposed by the later 1,000-case campaign.

### Adversarial testing and remediation

The assurance work was intentionally run red before remediation rather than reporting only green tests:

- **Run #65:** 12 adversarial test cases failed while 18 existing tests passed.
- The first remediation round addressed idempotency-key conflicts, requester execution, non-finite input, blank idempotency keys and multiple audit-analytics blind spots.
- **Run #68:** 30/30 tests passed after first-round remediation.
- **Run #69:** a second challenge round produced 6 failing adversarial cases while 30 tests passed.
- The second remediation round addressed audit-tail truncation, approval-provenance tampering and blank required audit-event fields.
- **Run #72:** 36/36 tests passed after second-round remediation.
- **Run #74:** 36/36 tests remained green after the executable assurance review was expanded.
- **Run #78:** a new escalating **1,000-case** campaign produced **700 passes and 300 failures** across three additional finding classes: unsafe Unicode control/format characters in action text, unsafe Unicode control/format characters in audit identity fields, and non-finite numbers in canonical audit evidence.
- Those three finding classes were remediated in the local and BigQuery-aligned paths and converted into targeted regression tests.
- **Run #82:** **47/47 regression tests**, **1,000/1,000 escalating campaign cases**, and **20/20 executable assurance controls** passed.

The full history is grouped into **15 distinct documented development/control findings** in assurance/adversarial_findings.json. These are findings against a self-built fictional system, not independent client-audit findings.

### 1,000-case escalating adversarial campaign

The campaign assigns difficulty scores **1 through 1,000**. Every later case includes one additional unrelated audit-event distractor while the primary control family rotates across ten domains: pre-retrieval ACLs, idempotency conflict handling, self-approval, requester execution, orphan-execution analytics, duplicate-approval analytics, audit tamper detection, action-text Unicode controls, audit-identity Unicode controls, and non-finite audit evidence.

The first run intentionally failed **300/1,000** cases, which produced three new finding classes rather than a cosmetic all-green result. After remediation, run #82 passed **1,000/1,000** cases at a maximum difficulty score of **1,000**.

### Executable Technology Assurance Control Review

Run #82 executed a separate deterministic assurance review:

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
| avg_latency_ms | 1.25 |

### Other CI gates

- frontend production build — success;
- deployment-script syntax validation — success;
- Docker Compose configuration validation — success;
- assurance-evidence artifact upload — success.

## What these results establish

They establish reproducible control-design and negative-testing evidence on the self-built fictional NEXUS environment. More importantly than the final pass rate, the CI history shows repeated red-to-green assurance cycles: weaknesses were deliberately sought, documented, remediated, converted into regression tests, and then re-performed at larger scale.

## What these results do **not** establish

They are not evidence of production operating effectiveness over a defined audit period, an independent audit opinion, SOC 1/SOC 2/SOX/ISAE 3402 compliance, real ERP/ICFR audit coverage, client deployment, production IAM lifecycle effectiveness, security against all attacks, or business ROI.

A real engagement would still require independent evidence, a defined audit population and period, sampling, control owners, reviewer sign-off, production identity/change records and customer-specific criteria.
