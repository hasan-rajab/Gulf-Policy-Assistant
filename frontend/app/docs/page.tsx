import Link from "next/link";

const sections = [
  ["Customer problem", "A fictional GCC bank has hundreds of internal policies across Arabic and English. Employees lose time searching portals and shared drives, may read outdated versions, and need answers that are fast without allowing an LLM to invent policy."],
  ["Requirements", "Bilingual Arabic/English interaction; approved-source grounding; citations; document ingestion; scalable retrieval; secure employee access; auditability; API-first integration; cloud deployment; measurable quality; and a demo path that can be shown without exposing customer data."],
  ["Architecture", "Employee → IAP-protected Next.js web tier → private FastAPI Cloud Run service → Gemini generation + embedding service → BigQuery Vector Search → approved policy corpus. The browser never needs direct access to the private RAG API in the production design."],
  ["Why this architecture", "It separates experience, orchestration, model access, and retrieval. Cloud Run keeps the application container portable and stateless. BigQuery makes retrieval live beside governed enterprise data and supports vector search. Gemini is called only after approved context is retrieved. Each component can evolve independently."],
  ["Alternatives considered", "Vertex AI / Gemini Enterprise managed RAG tooling is a strong alternative when the customer values managed ingestion/retrieval over direct SQL/data-platform control. Vertex AI Search is another option for enterprise search experiences. A standalone vector database can reduce query latency in some workloads but adds another governed data system. The prototype chooses BigQuery to make the retrieval mechanics explicit and inspectable."],
  ["Security considerations", "Production employee authentication is handled by IAP. The FastAPI service is private and invokable only by the web service identity. Use least-privilege IAM, Secret Manager, audit logs, document ACL propagation, retention controls, and input/output controls. Retrieved text is treated as untrusted data to reduce prompt-injection risk. Customer and confidential data must not be placed into the demo corpus."],
  ["Scalability considerations", "Cloud Run scales the stateless application tier horizontally. BigQuery vector indexes can accelerate large-corpus nearest-neighbor search. For higher QPS or tighter latency targets, measure exact-search versus ANN recall/latency, batch embeddings for ingestion, cache stable policy queries, and move conversation state to a managed durable store."],
  ["Deployment process", "Create/choose a Google Cloud project; enable Cloud Run, BigQuery, Gemini/Agent Platform, IAM Credentials, and IAP APIs; provision the BigQuery table; build containers into Artifact Registry; deploy FastAPI privately; grant the web service account Cloud Run Invoker; deploy Next.js with direct IAP protection; grant approved employees/groups access; then ingest approved documents."],
  ["Limitations", "The bundled policies are fictional. Local Demo Mode uses deterministic fallback embeddings and answer generation so the repository can be reviewed without credentials; it is not a benchmark of Gemini quality. Conversation history is in memory. Document-level ACL filtering is not implemented in the demo. PDF extraction is text-first and does not include table/layout understanding. Production residency, regulatory, model-risk, and retention decisions require the customer's actual requirements."],
  ["Recommended next steps", "Run a discovery workshop with HR, Security, Legal/Compliance, and employee personas. Build a 50–100 question bilingual golden set. Add per-document entitlements to retrieval. Compare BigQuery Vector Search with managed RAG tooling on recall, latency, cost, operations, and governance. Add Cloud Monitoring dashboards and quality regression gates. Pilot with a narrow policy domain before expanding corpus scope."],
];

export default function DocsPage() {
  return (
    <main className="docsShell">
      <aside className="docsRail">
        <Link href="/" className="backLink">← Back to demo</Link>
        <div className="brandRow"><div className="brandMark small">GH</div><div><strong>Customer brief</strong><span>Architecture & trade-offs</span></div></div>
        <nav>{sections.map(([title], i) => <a key={title} href={`#s${i}`}>{String(i + 1).padStart(2, "0")} {title}</a>)}</nav>
      </aside>
      <article className="docsContent">
        <div className="docsHero"><span className="eyebrow">CUSTOMER ENGINEERING PROTOTYPE</span><h1>Enterprise policy RAG,<br />designed for a GCC bank.</h1><p>This page is part of the deliverable: it explains the customer decision, not just the code.</p><div className="docPills"><span>Arabic + English</span><span>Gemini</span><span>BigQuery Vector Search</span><span>Cloud Run</span><span>IAP</span></div></div>
        <div className="archDiagram">
          <div><b>Employee</b><small>Arabic / English</small></div><i>→</i><div><b>Next.js</b><small>IAP web tier</small></div><i>→</i><div><b>FastAPI</b><small>Private Cloud Run</small></div><i>→</i><div className="stack"><b>Gemini</b><small>Grounded generation</small><em>+</em><b>BigQuery</b><small>Vector retrieval</small></div>
        </div>
        {sections.map(([title, body], i) => <section id={`s${i}`} className="docSection" key={title}><div className="sectionNumber">{String(i + 1).padStart(2, "0")}</div><div><h2>{title}</h2><p>{body}</p>{title === "Requirements" && <ul><li>Grounding before generation</li><li>Same-language answer behavior</li><li>Traceable citations and retrieval scores</li><li>Secure production topology</li><li>Evaluation that can become a CI quality gate</li></ul>}{title === "Recommended next steps" && <div className="nextStepCallout"><strong>Suggested customer workshop output</strong><span>Data sources → user groups → access model → bilingual golden questions → target latency/quality → pilot success criteria.</span></div>}</div></section>)}
        <footer className="docsFooter">Fictional customer data and policies · Built as a demonstrable reference architecture, not production banking software.</footer>
      </article>
    </main>
  );
}
