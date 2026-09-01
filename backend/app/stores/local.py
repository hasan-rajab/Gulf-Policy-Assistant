import json
from pathlib import Path
import re
import threading

import numpy as np

from app.core.access import AccessContext
from app.stores.base import SearchResult, StoredChunk, VectorStore


class LocalVectorStore(VectorStore):
    _LEXICAL_STOPWORDS = {
        "the", "a", "an", "is", "are", "what", "how", "can", "i", "to", "of", "for",
        "policy", "employee", "employees", "company", "bank",
        "ما", "هي", "هو", "هل", "كيف", "في", "من", "إلى", "الى", "على", "عن",
        "سياسة", "الموظف", "الموظفين", "البنك",
    }

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._chunks: list[StoredChunk] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        # StoredChunk defaults keep pre-NEXUS local indexes backward compatible.
        self._chunks = [StoredChunk(**item) for item in raw]

    def _save(self) -> None:
        payload = [vars(c) for c in self._chunks]
        self.path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def upsert(self, chunks: list[StoredChunk]) -> None:
        with self._lock:
            incoming_ids = {c.id for c in chunks}
            self._chunks = [c for c in self._chunks if c.id not in incoming_ids]
            self._chunks.extend(chunks)
            self._save()

    def _authorized_chunks(self, access: AccessContext | None) -> list[StoredChunk]:
        """Apply ACLs before semantic or lexical scoring."""
        return [chunk for chunk in self._chunks if chunk.is_authorized_for(access)]

    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        access: AccessContext | None = None,
    ) -> list[SearchResult]:
        chunks = self._authorized_chunks(access)
        if not chunks:
            return []
        q = np.asarray(query_embedding, dtype=np.float64)
        qnorm = np.linalg.norm(q) or 1.0
        scored: list[SearchResult] = []
        for chunk in chunks:
            v = np.asarray(chunk.embedding, dtype=np.float64)
            denom = (np.linalg.norm(v) or 1.0) * qnorm
            cosine = float(np.dot(v, q) / denom)
            score = max(0.0, min(1.0, cosine))
            scored.append(SearchResult(chunk=chunk, score=score))
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    @classmethod
    def _tokens(cls, text: str) -> list[str]:
        return [
            token
            for token in re.findall(r"[\w\u0600-\u06FF]+", (text or "").lower())
            if len(token) > 1 and token not in cls._LEXICAL_STOPWORDS
        ]

    def _lexical_search(
        self,
        query_text: str,
        top_k: int,
        access: AccessContext | None = None,
    ) -> list[SearchResult]:
        query_tokens = self._tokens(query_text)
        chunks = self._authorized_chunks(access)
        if not query_tokens or not chunks:
            return []

        qset = set(query_tokens)
        scored: list[SearchResult] = []
        for chunk in chunks:
            doc_tokens = self._tokens(f"{chunk.title} {chunk.text}")
            if not doc_tokens:
                continue
            dset = set(doc_tokens)
            overlap = len(qset & dset)
            if overlap == 0:
                continue
            precision = overlap / len(qset)
            coverage = overlap / max(1, min(len(dset), len(qset) * 4))
            score = min(1.0, 0.75 * precision + 0.25 * coverage)
            scored.append(SearchResult(chunk=chunk, score=score))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    def hybrid_search(
        self,
        query_text: str,
        query_embedding: list[float],
        top_k: int,
        access: AccessContext | None = None,
    ) -> list[SearchResult]:
        """Fuse ACL-scoped semantic and lexical rankings with RRF."""
        candidate_k = max(top_k * 3, 10)
        vector_results = self.search(query_embedding, candidate_k, access=access)
        lexical_results = self._lexical_search(query_text, candidate_k, access=access)

        by_id: dict[str, SearchResult] = {}
        vector_scores: dict[str, float] = {}
        lexical_scores: dict[str, float] = {}
        fused: dict[str, float] = {}
        rrf_k = 60.0

        for rank, result in enumerate(vector_results, start=1):
            by_id[result.chunk.id] = result
            vector_scores[result.chunk.id] = result.score
            fused[result.chunk.id] = fused.get(result.chunk.id, 0.0) + 1.0 / (rrf_k + rank)

        for rank, result in enumerate(lexical_results, start=1):
            by_id[result.chunk.id] = result
            lexical_scores[result.chunk.id] = result.score
            fused[result.chunk.id] = fused.get(result.chunk.id, 0.0) + 1.0 / (rrf_k + rank)

        if not fused:
            return []

        candidates: list[tuple[float, float, SearchResult]] = []
        for chunk_id, rrf_score in fused.items():
            vector_score = vector_scores.get(chunk_id, 0.0)
            lexical_score = lexical_scores.get(chunk_id, 0.0)
            confidence = max(vector_score, lexical_score)
            candidates.append(
                (
                    rrf_score,
                    confidence,
                    SearchResult(chunk=by_id[chunk_id].chunk, score=confidence),
                )
            )

        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [item[2] for item in candidates[:top_k]]

    def list_documents(self, access: AccessContext | None = None) -> list[dict]:
        grouped: dict[str, dict] = {}
        for c in self._authorized_chunks(access):
            item = grouped.setdefault(
                c.document_id,
                {
                    "document_id": c.document_id,
                    "title": c.title,
                    "chunks": 0,
                    "source_uri": c.source_uri,
                    "language": c.language,
                    "visibility": c.visibility,
                },
            )
            item["chunks"] += 1
            if item["language"] != c.language:
                item["language"] = "mixed"
        return sorted(grouped.values(), key=lambda x: x["title"])

    def count(self) -> int:
        return len(self._chunks)
