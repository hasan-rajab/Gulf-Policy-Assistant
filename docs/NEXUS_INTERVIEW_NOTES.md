# NEXUS Interview Notes

## Why retrieval-time authorization instead of filtering sources afterward?

Post-filtering can expose sensitive chunks to ranking, generation, logs, caches, or traces before they are removed. NEXUS reduces the searchable corpus first, so unauthorized evidence never becomes a retrieval candidate.

## Why RRF and then a reranker?

Semantic and lexical retrievers have different score distributions. RRF combines ranks without pretending those scores are directly comparable. A second deterministic reranker then improves ordering using query coverage, title relevance, language alignment, and the original retrieval confidence.

## Why keep the grounding threshold on the original confidence?

A ranking feature should not silently redefine evidence sufficiency. NEXUS uses reranking to order already-qualified evidence while preserving the calibrated retrieval score for the grounded/abstain decision.

## Why approval-gated tools?

Knowledge answering and side effects are different risk classes. A user can request an action, but the system persists it in `pending_approval`; a knowledge administrator must explicitly approve it before execution. Arbitrary model-generated tool names are rejected.

## Why hash-chain the local audit log?

An append-only database is useful, but modification can still occur. Chaining each event hash to the prior event makes later tampering detectable during verification. The cloud path additionally relies on warehouse/IAM retention controls.
