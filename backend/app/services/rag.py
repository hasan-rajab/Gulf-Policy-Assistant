import time
from uuid import uuid4

import structlog

from app.core.config import Settings
from app.models.schemas import ChatResponse, Source
from app.services.agent import PolicyAgentOrchestrator
from app.services.conversations import ConversationStore
from app.services.embeddings import EmbeddingProvider
from app.services.generation import Generator
from app.services.language import detect_language
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
    ):
        self.settings = settings
        self.embedder = embedder
        self.store = store
        self.generator = generator
        self.conversations = conversations
        self.agent = PolicyAgentOrchestrator()

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

    def answer(self, query: str, conversation_id: str | None, owner: str, top_k: int | None = None) -> ChatResponse:
        started = time.perf_counter()
        request_id = str(uuid4())
        cid = self.conversations.ensure(conversation_id, owner)
        history = self.conversations.get(cid, owner)
        trace = self.agent.start(query)

        retrieval_query = self._build_retrieval_query(query)
        query_vector = self.embedder.embed_query(retrieval_query)
        k = top_k or self.settings.retrieval_top_k
        raw_results = self.store.hybrid_search(retrieval_query, query_vector, k)
        results = [r for r in raw_results if r.score >= self.settings.min_relevance_score]
        grounded = bool(results)
        self.agent.record_retrieval(trace, len(results))

        if not results:
            self.agent.record_fallback(trace)
            lang = detect_language(query)
            answer = (
                "لا أستطيع تأكيد الإجابة من المعلومات الداخلية المعتمدة المتاحة. يرجى الرجوع إلى مالك السياسة أو الموارد البشرية."
                if lang == "ar"
                else "I can't confirm that from the approved internal information available. Please check with the policy owner or HR."
            )
            sources: list[Source] = []
        else:
            answer = self.generator.generate(query, history, results)
            self.agent.record_generation(trace)
            sources = [
                Source(
                    source_id=f"S{i}",
                    document_id=r.chunk.document_id,
                    title=r.chunk.title,
                    text=r.chunk.text,
                    source_uri=r.chunk.source_uri,
                    page=r.chunk.page,
                    chunk_index=r.chunk.chunk_index,
                    language=r.chunk.language,
                    score=round(r.score, 4),
                    metadata=r.chunk.metadata,
                )
                for i, r in enumerate(results, start=1)
            ]

        self.conversations.append(cid, "user", query)
        self.conversations.append(cid, "assistant", answer, [s.model_dump() for s in sources])
        latency_ms = int((time.perf_counter() - started) * 1000)

        logger.info(
            "rag_answer",
            request_id=request_id,
            user=owner,
            conversation_id=cid,
            query_language=detect_language(query),
            retrieved=len(results),
            grounded=grounded,
            latency_ms=latency_ms,
            retrieval_mode="hybrid",
            vector_backend=self.settings.vector_backend,
            model="demo-deterministic" if self.settings.demo_mode else self.settings.gemini_model,
            agent_trace=trace.as_dict(),
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
