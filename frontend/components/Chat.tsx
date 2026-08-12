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

function renderCitations(text: string) {
  const parts = text.split(/(\[S\d+\])/g);
  return parts.map((part, i) =>
    /^\[S\d+\]$/.test(part) ? <span className="inlineCitation" key={i}>{part}</span> : part,
  );
}

export default function Chat() {
  const [token, setToken] = useState<string | null>(null);
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
    const saved = localStorage.getItem("gcc-rag-token");
    if (saved) setToken(saved);
    fetch("/api/proxy/health").then(r => r.json()).then(setHealth).catch(() => null);
  }, []);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy]);

  const modeLabel = useMemo(() => {
    if (!health) return "Connecting";
    return health.demo_mode ? "Local demo fallback" : "Gemini + BigQuery";
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
    localStorage.setItem("gcc-rag-token", data.access_token);
    setToken(data.access_token);
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
        localStorage.removeItem("gcc-rag-token");
        setToken(null);
      }
      if (!res.ok) throw new Error(data.detail || "The assistant could not answer the request");
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
          <div className="brandMark">GH</div>
          <span className="eyebrow">CUSTOMER PROTOTYPE · GCC BANKING</span>
          <h1>Secure policy answers,<br />in Arabic and English.</h1>
          <p className="muted">A grounded enterprise RAG assistant for approved internal policy. This fictional demo shows the workflow a customer engineer could prototype before production hardening.</p>
          <div className="loginFields">
            <label>Employee email<input value={email} onChange={e => setEmail(e.target.value)} /></label>
            <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} /></label>
            <button className="primaryButton" onClick={() => login().catch(e => setError(e.message))}>Enter customer demo</button>
            {error && <div className="errorBanner">{error}</div>}
          </div>
          <div className="loginFoot">Production design: IAP employee identity → private Cloud Run API → Gemini + BigQuery Vector Search</div>
        </div>
      </main>
    );
  }

  return (
    <main className="appShell">
      <aside className="sidebar">
        <div>
          <div className="brandRow"><div className="brandMark small">GH</div><div><strong>Gulf Horizon</strong><span>Policy Assistant</span></div></div>
          <div className="navLabel">WORKSPACE</div>
          <button className="navItem active">Ask policy</button>
          <Link className="navItem" href="/docs">Customer docs</Link>
          <div className="navLabel">DEMO SCENARIOS</div>
          {DEMOS.map(d => <button className="demoNav" key={d.label} onClick={() => send(d.query)}><span>{d.label}</span><small dir={isArabic(d.query) ? "rtl" : "ltr"}>{d.query}</small></button>)}
        </div>
        <div className="sideFooter">
          <div className="statusRow"><span className="statusDot" />{modeLabel}</div>
          <small>{health?.vector_backend || "…"} retrieval</small>
        </div>
      </aside>

      <section className="chatArea">
        <header className="topbar">
          <div><span className="eyebrow">APPROVED INTERNAL KNOWLEDGE</span><h2>Policy intelligence</h2></div>
          <div className="topActions"><span className="shield">Grounded answers</span><Link href="/docs" className="ghostButton">Architecture</Link></div>
        </header>

        <div className="messages">
          {messages.length === 0 && (
            <div className="heroState">
              <div className="heroBadge">Customer Demo Mode</div>
              <h1>Ask the bank.<br /><span>Get the policy, not a guess.</span></h1>
              <p>Search approved Arabic and English policy content with source-level grounding. Try the prepared scenarios or ask your own question.</p>
              <div className="promptGrid">
                {DEMOS.map((d, i) => <button key={d.label} onClick={() => send(d.query)} className="promptCard" dir={isArabic(d.query) ? "rtl" : "ltr"}><span>{i === 0 ? "AR" : "EN"}</span><strong>{d.query}</strong><small>{i === 0 ? "Remote-work policy" : "Approval workflow"}</small></button>)}
              </div>
              <div className="architectureStrip"><span>Next.js</span><b>→</b><span>FastAPI</span><b>→</b><span>Gemini</span><b>+</b><span>Vector Search</span></div>
            </div>
          )}

          {messages.map((m, i) => (
            <article key={i} className={`message ${m.role}`}>
              <div className="messageAvatar">{m.role === "user" ? "YOU" : "AI"}</div>
              <div className="messageBody" dir={isArabic(m.content) ? "rtl" : "ltr"}>
                <div className="messageContent">{m.role === "assistant" ? renderCitations(m.content) : m.content}</div>
                {m.meta && <div className="answerMeta" dir="ltr"><span className={m.meta.grounded ? "good" : "warn"}>{m.meta.grounded ? "Grounded" : "Insufficient context"}</span><span>{m.meta.model}</span><span>{m.meta.retrieval_backend}</span><span>{m.meta.latency_ms} ms</span></div>}
                {!!m.sources?.length && <div className="sources"><div className="sourcesHeader" dir="ltr"><strong>Evidence used</strong><span>{m.sources.length} retrieved chunks</span></div>{m.sources.map(s => <SourceCard key={s.source_id + s.document_id + s.chunk_index} source={s} />)}</div>}
              </div>
            </article>
          ))}
          {busy && <article className="message assistant"><div className="messageAvatar">AI</div><div className="typing"><i/><i/><i/><span>Retrieving approved policy…</span></div></article>}
          {error && <div className="errorBanner">{error}</div>}
          <div ref={endRef} />
        </div>

        <form className="composer" onSubmit={onSubmit}>
          <div className="composerBox">
            <textarea value={query} onChange={e => setQuery(e.target.value)} placeholder="Ask about an approved policy… / اسأل عن سياسة معتمدة…" dir={isArabic(query) ? "rtl" : "ltr"} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(query); } }} />
            <button disabled={!query.trim() || busy} aria-label="Send">↑</button>
          </div>
          <div className="composerHint">Answers are restricted to retrieved approved policy context and may require human confirmation.</div>
        </form>
      </section>
    </main>
  );
}
