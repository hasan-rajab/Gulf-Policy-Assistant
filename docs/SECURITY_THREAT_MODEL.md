# Lightweight threat model

This is a prototype threat model, not a bank security assessment.

| Threat | Prototype control | Production follow-up |
|---|---|---|
| Unauthenticated employee access | Local JWT; IAP architecture for cloud mode | IAP/WIF, group access, context-aware access |
| Public access to RAG API | Private Cloud Run backend; web service account is invoker | Ingress policy, IAM review, service perimeter where required |
| Prompt injection in documents | System prompt treats retrieved text as untrusted data | Content scanning, Model Armor where appropriate, red-team eval set |
| Hallucinated policy | Retrieval threshold, context-only prompt, citations, unsupported-answer behavior | Human golden set, groundedness regression gates, escalation rules |
| Unauthorized document retrieval | Not implemented in demo | ACL metadata + pre-filtering / row-level security before vector search |
| Secret leakage | No secrets committed; environment-driven config | Secret Manager, rotation, least privilege |
| Excessive conversation retention | In-memory prototype history | Defined retention, encrypted durable store, user deletion/access policy |
| Sensitive upload | Fictional demo corpus only | DLP/content classification, approved ingestion workflow, audit logging |
| Cross-user conversation access | Conversation ownership check | Durable owner/tenant keys + authorization tests |
| Retrieval index poisoning | Admin-only ingestion API assumption | Signed/approved source pipeline, versioning, provenance, quarantine |
