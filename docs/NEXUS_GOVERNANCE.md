# NEXUS Governance Summary

NEXUS enforces least privilege across three planes:

- **knowledge plane:** identity-scoped retrieval before ranking
- **administration plane:** knowledge ingestion and evaluation restricted to knowledge administrators
- **action plane:** allowlisted requests require explicit approval before execution

Every plane emits audit events. User query text is represented in audit details by SHA-256 rather than being copied verbatim into the compliance log.
