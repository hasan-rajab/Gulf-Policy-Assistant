# NEXUS Architecture

```text
Enterprise identity
      |
      v
Server-side role / department resolution
      |
      v
Retrieval-time ACL filter
      |
      +--------------------------+
      |                          |
      v                          v
Semantic retrieval        Lexical retrieval
      |                          |
      +------------+-------------+
                   v
             RRF candidates
                   |
                   v
        deterministic reranker
                   |
                   v
       calibrated grounding gate
             |             |
            yes            no
             |             |
             v             v
 grounded generation   safe abstention
 + source citations    / human escalation
             |
             v
       audit event store

Separate side-effect plane:

user request -> allowlist/schema -> pending approval -> admin approval -> execution -> audit
```

## Why the separation matters

Retrieval, generation, and actions have different security properties. NEXUS does not give a language model direct authority over external systems. Retrieval is scoped before ranking, generation is constrained to authorized evidence, and actions cross an explicit human approval boundary.
