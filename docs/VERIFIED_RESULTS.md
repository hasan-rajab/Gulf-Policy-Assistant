# Verified results

This document records the strongest repository-backed validation evidence for NEXUS.

## Current reference validation

**GitHub Actions:** NEXUS CI — run #59  
**Date:** 1 September 2026  
**Commit:** `b7da2a70ac37c43f1d270e1a52c16fb060084f1d`  
**Workflow conclusion:** success

### Backend and security tests

```text
14 passed in 1.19s
```

### Strict RAG evaluation

The workflow ran a controlled **8-case** evaluation set and passed its strict metric gate.

| Metric | Result |
|---|---:|
| total_cases | 8 |
| retrieval_hit_at_k | 1.0 |
| citation_rate | 1.0 |
| citation_source_integrity_rate | 1.0 |
| grounding_decision_accuracy | 1.0 |
| language_match_rate | 1.0 |
| grounded_keyword_coverage | 1.0 |
| avg_latency_ms | 2.0 |

The same CI run also completed:

- frontend production build — success;
- Docker Compose / deployment validation — success.

## What these results establish

They show that the controlled fictional corpus and deterministic evaluation suite behaved as expected at the pinned commit, including retrieval, citation integrity, grounding decisions, language matching, and the tested security/backend behaviors.

## What these results do **not** establish

They are **not** evidence of:

- production-bank accuracy;
- production latency;
- regulatory approval or certification;
- safety across unseen enterprise data;
- security against all adversarial attacks;
- business ROI;
- autonomous production tool execution.

A real enterprise pilot would require a materially larger representative golden set, customer-specific access rules, production identity integration, security/red-team testing, operational monitoring, and explicit go/no-go thresholds.

## Historical note

An older local-results note in this file previously referenced August validation. This section supersedes it with the stronger, traceable September CI run so portfolio claims point to one reproducible reference.
