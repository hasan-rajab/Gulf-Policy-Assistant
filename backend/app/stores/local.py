import json
from pathlib import Path
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
