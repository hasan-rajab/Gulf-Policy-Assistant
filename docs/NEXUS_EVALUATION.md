# NEXUS Evaluation Contract

NEXUS treats GenAI behavior as a regression-tested software surface.

The CI evaluation set must preserve perfect scores on the checked-in deterministic demo corpus for:

- retrieval hit@k
- grounded-answer citation presence
- citation-to-returned-source integrity
- grounded vs abstained decision accuracy
- Arabic/English language matching
- required policy keyword coverage

These are deterministic portfolio regression gates, not claims about production accuracy on unseen enterprise data.

Security behavior is tested separately from answer quality. The backend test suite verifies that restricted chunks are removed before semantic and lexical scoring, that matching roles/departments can access them, that administrators can access them, and that arbitrary action names cannot enter the execution framework.
