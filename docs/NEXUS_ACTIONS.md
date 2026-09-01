# NEXUS Controlled Enterprise Actions

NEXUS separates knowledge retrieval from side-effecting enterprise actions.

A language model answer is never treated as authorization to change an external system. The action API uses explicit user requests, a fixed action registry, schema validation, persistence, idempotency, and a separate administrator approval transition.

## Lifecycle

```text
Employee request
      |
      v
Allowlist + payload validation
      |
      v
pending_approval
      |
      | knowledge_admin approval
      v
approved
      |
      | knowledge_admin execution
      v
executed
      |
      v
Audited handoff reference
```

## Portfolio-safe execution

The repository intentionally does not include credentials for a real HR or IT platform. Execution produces a deterministic `NEXUS-*` handoff reference that demonstrates the control plane without claiming an external integration that does not exist.

A production adapter can replace that final handoff with an approved service-management API while retaining the same request, approval, idempotency, authorization, and audit contracts.
