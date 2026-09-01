# NEXUS v2 Upgrade Status

Implemented on `nexus-production-upgrade`:

- retrieval-time role/department ACLs for local and BigQuery vector search
- administrator-only knowledge ingestion and evaluation
- second-stage deterministic reranking
- citation-to-source integrity evaluation
- append-only audit storage with local hash-chain verification
- allowlisted, idempotent, approval-gated enterprise actions
- non-root backend/frontend containers and health-gated Compose startup
- NEXUS UI/identity branding and role visibility
- CI regression coverage for security, retrieval, evaluation, and frontend build

This file is a branch implementation note and should be read together with the CI result and pull request before merge.
