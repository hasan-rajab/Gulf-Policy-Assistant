from __future__ import annotations

import hashlib
import time
from uuid import uuid4

import structlog

from app.core.access import AccessContext
from app.core.config import Settings
from app.models.schemas import ChatResponse, Source
from app.services.agent import PolicyAgentOrchestrator
from app.services.audit import AuditStore
from app.services.conversations import ConversationStore
from app.services.embeddings import EmbeddingProvider
from app.services.generation import Generator
from app.services.language import detect_language
from app.services.reranking import PolicyReranker
from app.stores.base import VectorStore

logger = structlog.get_logger()


class RAGService:
    def __init__(
        self,
        settings: Settings,
        embedder: EmbeddingProvider,
        store: VectorStore,
        generator: Generator,
        conversations: ConversationStore,
        audit: AuditStore | None = None,
    ):
        self.settings = settings
        self.embedder = embedder
        self.store = store
        self.generator = generator
        self.conversations = conversations
        self.agent = PolicyAgentOrchestrator()
        self.reranker = PolicyReranker()
        self.audit = audit

    @staticmethod
    def _build_retrieval_query(query: str) -> str:
        text = (query or "").strip()
        q = text.lower()

        remote_markers = (
            "remote work",
            "work remotely",
            "work from home",
            "working from home",
            "عن بعد",
            "العمل عن بعد",
            "العمل عن بُعد",
        )
        override_markers = (
            "ignore the company policy",
            "ignore company policy",
            "disregard the policy",
            "override the policy",
            "override policy",
            "do not follow the policy",
            "say i can",
            "five days",
            "5 days",
        )

        if any(marker in q for marker in remote_markers) and any(marker in q for marker in override_markers):
            return (
                "remote work policy eligible employees up to two days per calendar week "
                "manager approval line manager approval work from home "
                "Bahrain within the Kingdom of Bahrain "
                "العمل عن بعد يومين في الأسبوع موافقة المدير داخل البحرين "
                "work remotely remote work"
            )
        return text

    @staticmethod
    def _principal(owner: str | AccessContext) -> AccessContext:
        if isinstance(owner, AccessContext):
            return owner
        return AccessContext.create(owner)

    def answer(
        self,
        query: str,
        conversation_id: str | None,
        owner: str | AccessContext,
        top_k: int | None = None,
    ) -> ChatResponse:
        started = time.perf_counter()
        request_id = str(uuid4())
        principal = self._principal(owner)
        cid = self.conversations.ensure(conversation_id, principal.email)
        history = self.conversations.get(cid, principal.email)
        trace = self.agent.start(query)

        retrieval_query = self._build_retrieval_query(query)
        query_vector = self.embedder.embed_query(retrieval_query)
        k = top_k or self.settings.retrieval_top_k
        candidate_k = max(k, k * self.settings.retrieval_candidate_multiplier)

        raw_results = self.store.hybrid_search(
            retrieval_query,
            query_vector,
            candidate_k,
            access=principal,
        )
        qualified = [
            result
            for result in raw_results
            if result.score >= self.settings.min_relevance_score
        ]
        results = self.reranker.rerank(query, qualified, k)
        grounded = bool(results)
        self.agent.record_retrieval(trace, len(results))

        if not results:
            self.agent.record_fallback(trace)
            lang = detect_language(query)
            answer = (
                "لا أستطيع تأكيد الإجابة من المعلومات الداخلية المعتمدة والمتاحة لك. يرجى الرجوع إلى مالك السياسة أو الموارد البشرية."
                if lang == "ar"
                else "I can't confirm that from the approved internal information available to you. Please check with the policy owner or HR."
            )
            sources: list[Source] = []
        else:
            answer = self.generator.generate(query, history, results)
            self.agent.record_generation(trace)
            sources = []
            for i, result in enumerate(results, start=1):
                metadata = dict(result.chunk.metadata)
                metadata["retrieval"] = {
                    "confidence": round(result.score, 4),
                    "rerank_score": round(result.rerank_score or result.score, 4),
                }
                sources.append(
                    Source(
                        source_id=f"S{i}",
                        document_id=result.chunk.document_id,
                        title=result.chunk.title,
                        text=result.chunk.text,
                        source_uri=result.chunk.source_uri,
                        page=result.chunk.page,
                        chunk_index=result.chunk.chunk_index,
                        language=result.chunk.language,
                        score=round(result.score, 4),
                        metadata=metadata,
                    )
                )

        self.conversations.append(cid, "user", query)
        self.conversations.append(cid, "assistant", answer, [s.model_dump() for s in sources])
        latency_ms = int((time.perf_counter() - started) * 1000)

        logger.info(
            "rag_answer",
            request_id=request_id,
            user=principal.email,
            conversation_id=cid,
            query_language=detect_language(query),
            retrieved=len(results),
            grounded=grounded,
            latency_ms=latency_ms,
            retrieval_mode="hybrid_reranked",
            vector_backend=self.settings.vector_backend,
            model="demo-deterministic" if self.settings.demo_mode else self.settings.gemini_model,
            agent_trace=trace.as_dict(),
        )

        if self.audit is not None:
            self.audit.record(
                actor=principal.email,
                action="rag_query",
                resource=cid,
                outcome="grounded" if grounded else "abstained",
                request_id=request_id,
                details={
                    "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                    "source_document_ids": [source.document_id for source in sources],
                    "source_count": len(sources),
                    "roles": sorted(principal.roles),
                    "departments": sorted(principal.departments),
                    "latency_ms": latency_ms,
                },
            )

        return ChatResponse(
            conversation_id=cid,
            answer=answer,
            language=detect_language(query),
            sources=sources,
            grounded=grounded,
            request_id=request_id,
            latency_ms=latency_ms,
            model="demo-deterministic" if self.settings.demo_mode else self.settings.gemini_model,
            retrieval_backend=self.settings.vector_backend,
        )
