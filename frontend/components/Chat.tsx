"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import SourceCard from "./SourceCard";
import { isArabic } from "@/lib/language";
import { ChatResponse, UIMessage } from "@/lib/types";

const DEMOS = [
  { label: "Arabic demo", query: "ما هي سياسة العمل عن بعد؟" },
  { label: "English demo", query: "What is the approval process for remote work?" },
];

type Profile = { user_email: string; roles: string[]; departments: string[] };

function renderCitations(text: string) {
  const parts = text.split(/(\[S\d+\])/g);
  return parts.map((part, i) =>
    /^\[S\d+\]$/.test(part) ? <span className="inlineCitation" key={i}>{part}</span> : part,
  );
}

export default function Chat() {
  const [token, setToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [email, setEmail] = useState("employee@gulfhorizon.local");
  const [password, setPassword] = useState("Demo123!");
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState<any>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const saved = localStorage.getItem("nexus-token");
    const savedProfile = localStorage.getItem("nexus-profile");
    if (saved) setToken(saved);
    if (savedProfile) {
      try { setProfile(JSON.parse(savedProfile)); } catch { localStorage.removeItem("nexus-profile"); }
    }
    fetch("/api/proxy/health").then(r => r.json()).then(setHealth).catch(() => null);
  }, []);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy]);

  const modeLabel = useMemo(() => {
    if (!health) return "Connecting";
    return health.demo_mode ? "Local governed demo" : "Gemini + BigQuery";
  }, [health]);

  async function login() {
    setError("");
    const res = await fetch("/api/proxy/api/auth/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Login failed");
    const nextProfile: Profile = {
      user_email: data.user_email,
      roles: data.roles || [],
      departments: data.departments || [],
    };
    localStorage.setItem("nexus-token", data.access_token);
    localStorage.setItem("nexus-profile", JSON.stringify(nextProfile));
    setToken(data.access_token);
    setProfile(nextProfile);
  }

  async function send(text: string) {
    if (!text.trim() || busy) return;
    setBusy(true);
    setError("");
    setMessages(prev => [...prev, { role: "user", content: text.trim() }]);
    setQuery("");
    try {
      const res = await fetch("/api/proxy/api/chat", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          ...(token ? { authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ query: text.trim(), conversation_id: conversationId }),
      });
      const data = await res.json();
      if (res.status === 401) {
        localStorage.removeItem("nexus-token");
        localStorage.removeItem("nexus-profile");
        setToken(null);
        setProfile(null);
      }
      if (!res.ok) throw new Error(data.detail || "NEXUS could not answer the request");
      const answer = data as ChatResponse;
      setConversationId(answer.conversation_id);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: answer.answer,
        sources: answer.sources,
        meta: {
          grounded: answer.grounded,
          latency_ms: answer.latency_ms,
          model: answer.model,
          retrieval_backend: answer.retrieval_backend,
        },
      }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await send(query);
  }

  if (!token && health?.demo_mode) {
    return (
      <main className="loginShell">
        <div className="loginPanel">
          <div className="brandMark">NX</div>
          <span className="eyebrow">NEXUS · GOVERNED ENTERPRISE AI</span>
          <h1>Enterprise answers,<br />scoped to your access.</h1>
          <p className="muted">A bilingual GCC enterprise assistant with retrieval-time authorization, grounded citations, safe abstention, auditability, and approval-gated actions.</p>
          <div className="loginFields">
            <label>Employee email<input value={email} onChange={e => setEmail(e.target.value)} /></label>
            <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} /></label>
            <button className="primaryButton" onClick={() => login().catch(e => setError(e.message))}>Enter NEXUS</button>
            {error && <div className="errorBanner">{error}</div>}
          </div>
          <div className="loginFoot">Production path: enterprise identity → retrieval ACLs → hybrid search + reranking → grounded generation → audit trail</div>
        </div>
      </main>
    );
  }

  return (
    <main className="appShell">
      <aside className="sidebar">
        <div>
          <div className="brandRow"><div className="brandMark small">NX</div><div><strong>NEXUS</strong><span>Enterprise AI</span></div></div>
          <div className="navLabel">WORKSPACE</div>
          <button className="navItem active">Ask knowledge</button>
          <Link className="navItem" href="/docs">Architecture</Link>
          <div className="navLabel">DEMO SCENARIOS</div>
          {DEMOS.map(d => <button className="demoNav" key={d.label} onClick={() => send(d.query)}><span>{d.label}</span><small dir={isArabic(d.query) ? "rtl" : "ltr"}>{d.query}</small></button>)}
        </div>
        <div className="sideFooter">
          <div className="statusRow"><span className="statusDot" />{modeLabel}</div>
          <small>{health?.retrieval || "ACL-scoped retrieval"}</small>
          {profile && <small>{profile.roles.join(" · ")} {profile.departments.length ? `| ${profile.departments.join(", ")}` : ""}</small>}
        </div>
      </aside>

      <section className="chatArea">
        <header className="topbar">
          <div><span className="eyebrow">AUTHORIZED INTERNAL KNOWLEDGE</span><h2>Enterprise intelligence</h2></div>
          <div className="topActions"><span className="shield">ACL scoped · grounded</span><Link href="/docs" className="ghostButton">Architecture</Link></div>
        </header>

        <div className="messages">
          {messages.length === 0 && (
            <div className="heroState">
              <div className="heroBadge">Governed Enterprise AI</div>
              <h1>Ask the enterprise.<br /><span>Get evidence you are allowed to see.</span></h1>
              <p>NEXUS searches only the policy corpus authorized for your identity, reranks the evidence, cites its answer, and abstains when approved support is insufficient.</p>
              <div className="promptGrid">
                {DEMOS.map((d, i) => <button key={d.label} onClick={() => send(d.query)} className="promptCard" dir={isArabic(d.query) ? "rtl" : "ltr"}><span>{i === 0 ? "AR" : "EN"}</span><strong>{d.query}</strong><small>{i === 0 ? "Bilingual retrieval" : "Grounded workflow"}</small></button>)}
              </div>
              <div className="architectureStrip"><span>RBAC</span><b>→</b><span>Hybrid RAG</span><b>→</b><span>Reranker</span><b>→</b><span>Guardrails</span><b>→</b><span>Audit</span></div>
            </div>
          )}

          {messages.map((m, i) => (
            <article key={i} className={`message ${m.role}`}>
              <div className="messageAvatar">{m.role === "user" ? "YOU" : "NX"}</div>
              <div className="messageBody" dir={isArabic(m.content) ? "rtl" : "ltr"}>
                <div className="messageContent">{m.role === "assistant" ? renderCitations(m.content) : m.content}</div>
                {m.meta && <div className="answerMeta" dir="ltr"><span className={m.meta.grounded ? "good" : "warn"}>{m.meta.grounded ? "Grounded" : "Safe abstention"}</span><span>{m.meta.model}</span><span>{m.meta.retrieval_backend}</span><span>{m.meta.latency_ms} ms</span></div>}
                {!!m.sources?.length && <div className="sources"><div className="sourcesHeader" dir="ltr"><strong>Authorized evidence used</strong><span>{m.sources.length} reranked chunks</span></div>{m.sources.map(s => <SourceCard key={s.source_id + s.document_id + s.chunk_index} source={s} />)}</div>}
              </div>
            </article>
          ))}
          {busy && <article className="message assistant"><div className="messageAvatar">NX</div><div className="typing"><i/><i/><i/><span>Authorizing and retrieving evidence…</span></div></article>}
          {error && <div className="errorBanner">{error}</div>}
          <div ref={endRef} />
        </div>

        <form className="composer" onSubmit={onSubmit}>
          <div className="composerBox">
            <textarea value={query} onChange={e => setQuery(e.target.value)} placeholder="Ask authorized enterprise knowledge… / اسأل عن المعرفة المصرح بها…" dir={isArabic(query) ? "rtl" : "ltr"} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(query); } }} />
            <button disabled={!query.trim() || busy} aria-label="Send">↑</button>
          </div>
          <div className="composerHint">NEXUS retrieves only identity-authorized evidence. Unsupported requests abstain or route to controlled human approval.</div>
        </form>
      </section>
    </main>
  );
}
