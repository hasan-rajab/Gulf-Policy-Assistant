import Link from "next/link";

const sections = [
  ["Problem", "Enterprise employees need fast answers from internal policy without exposing restricted documents or allowing an LLM to invent policy. NEXUS treats this as an authorization-and-evidence problem before it treats it as a generation problem."],
  ["Identity & access", "The web tier establishes employee identity. The backend resolves roles and departments from trusted server-side configuration or an enterprise directory. Restricted documents are removed from the searchable corpus before semantic or lexical scoring; client-supplied role headers are not trusted."],
  ["Retrieval", "NEXUS combines semantic and lexical retrieval with Reciprocal Rank Fusion, then applies a deterministic second-stage reranker using retrieval confidence, query coverage, title relevance, and language alignment. The calibrated retrieval score—not the rerank score—controls whether evidence is sufficient to answer."],
  ["Grounding", "Only authorized, sufficiently relevant chunks reach generation. Answers include inline source citations. If evidence is insufficient, NEXUS abstains and routes the user toward the policy owner instead of increasing model creativity."],
  ["Controlled actions", "Knowledge retrieval and side effects are separate security planes. Employees can request only registered actions. Requests are schema-validated, persisted, idempotent, and remain pending until a knowledge administrator explicitly approves them. Execution uses guarded state transitions and produces an auditable handoff reference in the portfolio demo."],
  ["Auditability", "Login, RAG access, ingestion, evaluation, approvals, and executions emit audit events. Local mode stores an append-only SQLite trail with a SHA-256 hash chain; the Google Cloud path stores audit events in BigQuery. Query text is represented in audit records by a hash rather than copied verbatim."],
  ["Google Cloud path", "IAP-protected Next.js → private FastAPI on Cloud Run → server-side entitlements → ACL-prefiltered BigQuery Vector Search → Gemini → governed response. BigQuery also stores audit events and action-workflow state so Cloud Run remains stateless."],
  ["Evaluation", "CI compiles the backend, runs security and retrieval tests, ingests the fictional policy corpus, enforces retrieval/grounding/citation/language regression metrics, validates citation-to-source integrity, and builds the Next.js production frontend."],
  ["Threat model", "Key failure modes include prompt injection, unauthorized document retrieval, user-supplied privilege claims, knowledge-base poisoning, unsupported answers, arbitrary tool execution, duplicate side effects, and approval bypass. NEXUS has explicit controls and regression tests for these boundaries."],
  ["Limitations", "The bundled corpus and quality metrics are synthetic portfolio evidence, not production banking benchmarks. Production entitlements must come from a real directory, customer-specific IAM/residency/retention controls must be configured, and the controlled-action demo uses a handoff reference rather than pretending to call a live HR or IT platform."],
];

export default function DocsPage() {
  return (
    <main className="docsShell">
      <aside className="docsRail">
        <Link href="/" className="backLink">← Back to NEXUS</Link>
        <div className="brandRow"><div className="brandMark small">NX</div><div><strong>NEXUS</strong><span>Architecture & governance</span></div></div>
        <nav>{sections.map(([title], i) => <a key={title} href={`#s${i}`}>{String(i + 1).padStart(2, "0")} {title}</a>)}</nav>
      </aside>
      <article className="docsContent">
        <div className="docsHero">
          <span className="eyebrow">GOVERNED ENTERPRISE AI</span>
          <h1>Authorization before retrieval.<br />Evidence before generation.</h1>
          <p>NEXUS is a bilingual enterprise RAG and controlled-action reference architecture designed around least privilege, measurable grounding, and explicit human approval.</p>
          <div className="docPills"><span>Arabic + English</span><span>Retrieval ACLs</span><span>Hybrid + reranking</span><span>Audit trail</span><span>Approval gates</span></div>
        </div>
        <div className="archDiagram">
          <div><b>Identity</b><small>IAP / demo JWT</small></div><i>→</i>
          <div><b>ACL scope</b><small>Role + department</small></div><i>→</i>
          <div><b>Hybrid RAG</b><small>RRF + reranker</small></div><i>→</i>
          <div className="stack"><b>Grounded AI</b><small>Citations / abstention</small><em>+</em><b>Control plane</b><small>Audit + approvals</small></div>
        </div>
        {sections.map(([title, body], i) => (
          <section id={`s${i}`} className="docSection" key={title}>
            <div className="sectionNumber">{String(i + 1).padStart(2, "0")}</div>
            <div>
              <h2>{title}</h2>
              <p>{body}</p>
              {title === "Threat model" && <ul><li>Restricted chunks never enter unauthorized retrieval candidates</li><li>Knowledge ingestion and evaluation require administrator entitlement</li><li>Unknown action names and payload fields are rejected</li><li>Actions cannot execute from pending state</li><li>Idempotency keys prevent duplicate user requests</li></ul>}
              {title === "Evaluation" && <div className="nextStepCallout"><strong>Release gate</strong><span>Security tests + strict bilingual RAG metrics + citation-source integrity + frontend production build must all pass before merge.</span></div>}
            </div>
          </section>
        ))}
        <footer className="docsFooter">Fictional policy corpus · Portfolio reference architecture · No claim of live customer deployment.</footer>
      </article>
    </main>
  );
}
