# NEXUS — Executive AI Consulting Case Study

## Executive summary

**Client scenario:** Gulf Horizon Bank, Bahrain *(fictional portfolio scenario)*  
**Challenge:** Employees need fast access to Arabic and English policy knowledge, but a general-purpose LLM creates unacceptable risks around unauthorized retrieval, unsupported answers, and uncontrolled actions.  
**Recommendation:** Start with a governed, read-first enterprise RAG capability. Enforce authorization before retrieval, require grounded evidence and citations, abstain when evidence is insufficient, and introduce side-effecting actions only through approval-gated workflows.

NEXUS is the working reference implementation behind that recommendation.

> **Claims boundary:** Gulf Horizon Bank and all business figures in this case study are fictional. Technical validation results are drawn from the NEXUS repository and controlled evaluation suite. They are not claims of production deployment or client outcomes.

---

## 1. Situation

The fictional bank has policy content distributed across Arabic and English sources. Employees lose time locating approved guidance, while compliance and technology teams need assurance that:

- employees only retrieve documents they are authorized to access;
- generated answers are grounded in approved evidence;
- unsupported questions do not produce confident fabricated answers;
- citations point to evidence actually returned by the system;
- AI-generated text cannot directly authorize enterprise actions;
- access, decisions, approvals, and actions remain auditable.

The core problem is therefore not "build a chatbot." It is:

> **How can an enterprise use generative AI for knowledge access without weakening existing authorization, governance, and accountability controls?**

---

## 2. Discovery questions

Before recommending technology, I would validate:

### Business
- Which employee groups create the highest policy-search workload?
- Which policy domains generate the most repetitive questions?
- What is the cost of a wrong answer versus a slow answer?
- Which use cases require answer-only assistance versus workflow execution?

### Data
- Where are approved documents stored?
- How are versions, owners, and approval status represented?
- Are Arabic and English documents equivalent translations or separate policies?
- Which entitlements are role-, department-, country-, or group-specific?

### Risk and governance
- What information must never be sent to a generative model?
- What retention, residency, and audit requirements apply?
- What minimum citation granularity is required?
- Which actions require human approval?

### Success criteria
- retrieval recall;
- grounded-answer accuracy;
- citation integrity;
- unsupported-question abstention;
- latency;
- escalation rate;
- adoption;
- measurable time saved.

---

## 3. Options considered

| Option | Strength | Limitation | Consulting view |
|---|---|---|---|
| Traditional enterprise search | Predictable and low generative risk | Users still interpret documents manually | Useful baseline, but limited productivity gain |
| Fine-tuned LLM | Can adapt style/behavior | Does not inherently solve live knowledge freshness or document authorization | Not the first recommendation for policy retrieval |
| Broad RAG | Better knowledge grounding | Can still leak restricted evidence if authorization occurs after retrieval | Insufficient without retrieval-time controls |
| Governed RAG | Grounded answers with enterprise access controls | Requires metadata discipline and evaluation | **Recommended first phase** |
| Autonomous agent | Can execute multi-step work | Higher operational, security, and approval risk | Introduce only after knowledge quality and controls are proven |

---

## 4. Recommendation

Implement a phased **governed RAG → copilot → approval-gated action** model.

### Phase 1 — Read-only governed knowledge
- enterprise identity and server-side entitlements;
- document ACL enforcement before retrieval scoring;
- Arabic/English hybrid retrieval;
- evidence thresholding;
- grounded responses with citations;
- safe abstention;
- audit trail.

### Phase 2 — Department copilot
- higher-volume policy domains;
- larger golden evaluation set;
- user feedback and escalation;
- production observability;
- adoption and productivity measurement.

### Phase 3 — Controlled actions
- fixed action allowlist;
- strict payload schemas;
- human approval;
- idempotency;
- guarded state transitions;
- audit of request → approval → execution.

This sequencing avoids jumping directly from "chatbot" to autonomous enterprise agent.

---

## 5. Solution architecture

```text
Enterprise identity
      ↓
Server-side roles / departments
      ↓
Authorized document scope
      ↓
Semantic + lexical retrieval
      ↓
Reciprocal Rank Fusion
      ↓
Deterministic reranking
      ↓
Evidence sufficiency gate
      ├── sufficient → grounded answer + citations
      └── insufficient → abstain / escalate
      ↓
Audit event

Separate side-effect plane:

Action request
      ↓
Allowlist + schema validation
      ↓
pending_approval
      ↓
authorized human approval
      ↓
approved
      ↓
guarded execution
      ↓
audited handoff / result
```

### Critical design decision

**Authorization is applied before semantic or lexical scoring.**

Retrieving restricted chunks and filtering them afterward is weaker because sensitive text may already have entered candidate generation, reranking, model context, traces, logs, or caches.

---

## 6. Governance model

The NEXUS design addresses five enterprise control questions:

1. **Who is the user?**  
   Identity is resolved server-side.

2. **What may they retrieve?**  
   Role and department ACLs constrain the candidate corpus before scoring.

3. **When may the model answer?**  
   Evidence must pass a sufficiency threshold; otherwise the system abstains.

4. **When may the system act?**  
   Generated text is never treated as authorization. Actions require allowlisted schemas and approval.

5. **Can decisions be reconstructed later?**  
   Requests, decisions, and workflow transitions are auditable, with a tamper-evident local audit chain.

---

## 7. Verified technical evidence

The controlled NEXUS validation set records:

- **14/14 backend and security tests passed**
- **8/8 deterministic RAG evaluation cases passed**
- combined: **22/22 automated checks**

The controlled eight-case evaluation reported 1.000 on:

- retrieval hit@k;
- citation rate;
- citation-to-source integrity;
- grounding decision accuracy;
- language match rate;
- grounded keyword coverage.

Average deterministic local latency recorded for that controlled evaluation was **2.0 ms**.

These results validate expected behavior on the bundled fictional corpus. They do **not** represent production accuracy, security guarantees, or real-enterprise latency.

---

## 8. What I would measure in a real pilot

### Business KPIs
- time spent searching for policy information;
- policy-related support tickets;
- first-contact resolution;
- employee adoption;
- hours of capacity released.

### AI quality KPIs
- retrieval recall;
- grounded-answer accuracy;
- citation integrity;
- abstention accuracy;
- escalation rate;
- language-match performance.

### Risk KPIs
- unauthorized retrieval attempts blocked;
- prompt-injection test pass rate;
- policy/version freshness;
- action approval exceptions;
- audit completeness.

---

## 9. Executive recommendation

The near-term value is not "autonomous AI." It is **trusted access to enterprise knowledge**.

A controlled rollout should prove three things before expanding autonomy:

1. the right employee receives the right evidence;
2. the system reliably knows when it lacks enough evidence to answer;
3. measurable user time is saved without weakening governance.

Only then should the enterprise expand from read-only assistance into approval-gated workflows and broader automation.
