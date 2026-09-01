import json
from pathlib import Path
import re
import threading

import numpy as np

from app.stores.base import SearchResult, StoredChunk, VectorStore


class LocalVectorStore(VectorStore):
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

    def search(self, query_embedding: list[float], top_k: int) -> list[SearchResult]:
        if not self._chunks:
            return []
        q = np.asarray(query_embedding, dtype=np.float64)
        qnorm = np.linalg.norm(q) or 1.0
        scored: list[SearchResult] = []
        for chunk in self._chunks:
            v = np.asarray(chunk.embedding, dtype=np.float64)
            denom = (np.linalg.norm(v) or 1.0) * qnorm
            cosine = float(np.dot(v, q) / denom)
            score = max(0.0, min(1.0, cosine))
            scored.append(SearchResult(chunk=chunk, score=score))
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[\w\u0600-\u06FF]+", (text or "").lower())

    def _lexical_search(self, query_text: str, top_k: int) -> list[SearchResult]:
        query_tokens = self._tokens(query_text)
        if not query_tokens or not self._chunks:
            return []

        qset = set(query_tokens)
        scored: list[SearchResult] = []
        for chunk in self._chunks:
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
    ) -> list[SearchResult]:
        """Fuse semantic and lexical rankings with reciprocal-rank fusion.

        RRF avoids pretending the vector and lexical scores share the same
        calibration. The final score is normalized to [0, 1] for compatibility
        with the existing grounding threshold.
        """
        candidate_k = max(top_k * 3, 10)
        vector_results = self.search(query_embedding, candidate_k)
        lexical_results = self._lexical_search(query_text, candidate_k)

        by_id: dict[str, SearchResult] = {}
        fused: dict[str, float] = {}
        rrf_k = 60.0

        for rank, result in enumerate(vector_results, start=1):
            by_id[result.chunk.id] = result
            fused[result.chunk.id] = fused.get(result.chunk.id, 0.0) + 1.0 / (rrf_k + rank)

        for rank, result in enumerate(lexical_results, start=1):
            by_id[result.chunk.id] = result
            fused[result.chunk.id] = fused.get(result.chunk.id, 0.0) + 1.0 / (rrf_k + rank)

        if not fused:
            return []

        max_rrf = 2.0 / (rrf_k + 1.0)
        ranked = [
            SearchResult(chunk=by_id[chunk_id].chunk, score=min(1.0, score / max_rrf))
            for chunk_id, score in fused.items()
        ]
        ranked.sort(key=lambda r: r.score, reverse=True)
        return ranked[:top_k]

    def list_documents(self) -> list[dict]:
        grouped: dict[str, dict] = {}
        for c in self._chunks:
            item = grouped.setdefault(
                c.document_id,
                {
                    "document_id": c.document_id,
                    "title": c.title,
                    "chunks": 0,
                    "source_uri": c.source_uri,
                    "language": c.language,
                },
            )
            item["chunks"] += 1
            if item["language"] != c.language:
                item["language"] = "mixed"
        return sorted(grouped.values(), key=lambda x: x["title"])

    def count(self) -> int:
        return len(self._chunks)
