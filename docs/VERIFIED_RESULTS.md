# Verified results

This document records the measured results captured during the project validation on 12 August 2026.

## Verified local evaluation summary

- 5 passed
- total_cases: 8
- retrieval_hit_at_k: 1.0
- citation_rate: 1.0
- grounding_decision_accuracy: 1.0
- language_match_rate: 1.0
- grounded_keyword_coverage: 1.0

## Persistence validation

The following behavior was explicitly validated after restarting the backend:

- English cybersecurity question: correct answer with 30-minute reporting requirement
- Arabic cybersecurity question: correct answer with 30-minute reporting requirement
- answer was grounded using a single approved citation
- the policy document remained visible in the document list after restart
- both backend and frontend containers remained running and healthy

## Important distinction

The values above are measured results from this repository's local demo environment and evaluation set. They are not a claim that a production bank deployment has been approved, scaled, or certified. The production architecture described elsewhere in this repository is a future implementation path that must be validated against the customer's corpus, security requirements, procurement controls, and operating model.
