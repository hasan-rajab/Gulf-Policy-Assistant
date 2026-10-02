# Verified results

This document records the strongest repository-backed validation evidence for NEXUS.

## Current reference validation

**GitHub Actions:** NEXUS CI — run #63  
**Date:** 2 October 2026  
**Validated commit:** `b028674b05a253fc7a799db7982d3e9aba7ff8a5`  
**Workflow conclusion:** success

This run is the reference validation for the technology-assurance control pack introduced in pull request #5.

### Backend, security and assurance tests

```text
18 passed in 1.48s
```

The test suite includes retrieval-time access control, authorization behavior, approval-gated actions, four-eyes/self-approval prevention, idempotency, action allowlisting, audit-chain integrity, audit-exception analytics, and the executable assurance review.

### Executable Technology Assurance Control Review

The CI run executed the deterministic NEXUS Technology Assurance Control Review and produced a machine-readable evidence artifact.

| Result | Value |
|---|---:|
| controls tested | 13 |
| controls passed | 13 |
| controls failed | 0 |
| overall result | passed |
| structured audit events analyzed in valid workflow | 7 |
| control exceptions in valid workflow | 0 |

The 13 tested controls cover:

- pre-retrieval logical access for unauthorized and authorized principals;
- execution-before-approval prevention;
- admin-only approval;
- four-eyes segregation of duties / self-approval prevention;
- replay prevention through idempotency;
- action allowlisting and schema validation;
- valid pending -> approved -> executed state transition;
- audit hash-chain integrity;
- deterministic control-exception analytics;
- controlled audit-tampering detection;
- CI/change-management quality gates;
- AI-assurance evaluation coverage.

The generated CI artifact is named `nexus-technology-assurance-report`.

### Strict RAG evaluation

The same workflow ran the controlled **8-case** evaluation set and passed its strict metric gate.

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

The same run also completed:

- frontend production build — success;
- deployment-script syntax validation — success;
- Docker Compose configuration validation — success;
- assurance-evidence artifact upload — success.

## What these results establish

They establish that, at the validated commit, the controlled fictional system behaved as expected for the explicitly tested backend/security paths, the eight-case RAG evaluation, and the thirteen-control technology-assurance review.

In particular, the automated evidence demonstrates the tested mechanics of authorization before retrieval, independent approval, replay protection, audit integrity, exception analytics, and controlled AI evaluation.

## What these results do **not** establish

They are **not** evidence of:

- production-enterprise accuracy or latency;
- production operating effectiveness over a defined audit period;
- a SOC 1, SOC 2, SOX, ISAE 3402, COBIT, COSO, regulatory, or certification conclusion;
- real ERP or financially significant process coverage;
- enterprise IAM joiner/mover/leaver effectiveness;
- security against all adversarial attacks;
- business ROI;
- autonomous production tool execution;
- independent auditor assurance.

A real engagement would require a materially larger representative evaluation set, customer-specific access rules, production identity integration, audit-period populations and sampling, independent evidence, security/red-team testing, operational monitoring, control owners, and explicit go/no-go criteria.

## Historical reference

Run #59 on 1 September 2026 previously established 14 passing backend/security tests and the same eight-case strict RAG metric gate. Run #63 supersedes it as the strongest reference because it adds four assurance regression tests and a separately executed 13-control technology-assurance review.
