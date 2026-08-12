# ADR-001 — BigQuery Vector Search as the explicit retrieval implementation

## Status

Prototype decision. Re-evaluate with the customer's corpus and non-functional requirements.

## Decision

Use BigQuery as the production retrieval implementation in this reference prototype while keeping the vector-store interface replaceable.

## Rationale

1. It makes the RAG mechanics inspectable: chunks, embeddings, metadata, SQL, distance, and indexes are visible to the customer.
2. It fits customers already governing substantial data in BigQuery.
3. BigQuery supports vector similarity search and vector indexes, so the prototype can move from exact search toward ANN without replacing the application contract.
4. It gives a useful customer conversation about data governance, IAM, row/column security, cost, latency, and scale instead of hiding retrieval inside the UI.

## Alternative: managed RAG tooling

Use Google's managed RAG capabilities when the customer prioritizes managed corpus ingestion, retrieval operations, and agent-platform integration over direct SQL control. The application keeps `EmbeddingProvider` and `VectorStore` abstractions so this can be evaluated without redesigning the frontend or REST contract.

## Alternative: dedicated vector database

A dedicated vector database can be appropriate when latency/QPS requirements, filtering patterns, or existing platform standards justify another serving system. It introduces another governed datastore, operational surface, and cost model.

## What to measure before production

- bilingual retrieval recall@k and nDCG/MRR
- exact versus ANN recall/latency
- query latency distribution under expected concurrency
- ingestion/re-embedding throughput and cost
- metadata/ACL filtering behavior
- operational complexity and incident ownership
