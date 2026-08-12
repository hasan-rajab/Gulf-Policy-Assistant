# Customer discovery guide

A Customer Engineer should validate these before calling the prototype production-ready.

## Business and users

- Which employee groups need the assistant first: HR, branch staff, operations, compliance, technology?
- Which policy questions consume the most time today?
- What is the cost of a wrong answer versus a slow answer?
- Should the assistant answer only, or also link to workflows such as HR requests?

## Data and governance

- Where are approved documents stored today?
- How is document approval/versioning represented?
- Are Arabic and English documents translations of one another or independent policies?
- Which documents have group-, role-, country-, or department-level entitlements?
- What content must never be sent to a generative model?
- What retention and data-residency requirements apply?

## Quality

- What does “correct” mean: exact policy language, operational summary, or both?
- What questions should deliberately return “I cannot confirm”?
- What citation granularity is required: document, page, paragraph, section?
- What Arabic varieties appear in employee questions?
- What are acceptable retrieval recall, groundedness, latency, and escalation rates?

## Security

- Identity source and employee groups?
- Need for Workforce Identity Federation?
- Context-aware access requirements?
- Document-level ACL propagation strategy?
- Audit-log and conversation-retention requirements?
- DLP, Model Armor, VPC Service Controls, or CMEK requirements?

## Pilot success criteria

A sensible first pilot might use one policy domain, 50–100 bilingual golden questions, clearly scoped employee groups, and explicit go/no-go thresholds for retrieval recall, grounded-answer accuracy, latency, and unsupported-question handling.
