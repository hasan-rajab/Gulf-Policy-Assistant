from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.access import AccessContext


@dataclass
class StoredChunk:
    id: str
    document_id: str
    title: str
    text: str
    embedding: list[float]
    chunk_index: int
    page: int | None = None
    language: str = "mixed"
    source_uri: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    visibility: str = "public"
    allowed_roles: list[str] = field(default_factory=list)
    allowed_departments: list[str] = field(default_factory=list)

    def is_authorized_for(self, access: AccessContext | None) -> bool:
        if access is None:
            # Internal maintenance/evaluation calls that do not pass identity are
            # least-privilege by default: only public chunks are searchable.
            return (self.visibility or "public").lower() == "public"
        return access.can_read(
            self.visibility,
            self.allowed_roles,
            self.allowed_departments,
        )


@dataclass
class SearchResult:
    chunk: StoredChunk
    score: float
    rerank_score: float | None = None


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, chunks: list[StoredChunk]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        access: AccessContext | None = None,
    ) -> list[SearchResult]:
        raise NotImplementedError

    def hybrid_search(
        self,
        query_text: str,
        query_embedding: list[float],
        top_k: int,
        access: AccessContext | None = None,
    ) -> list[SearchResult]:
        """Hybrid retrieval hook with authorization-aware fallback."""
        return self.search(query_embedding, top_k, access=access)

    @abstractmethod
    def list_documents(self, access: AccessContext | None = None) -> list[dict]:
        raise NotImplementedError

    def count(self) -> int:
        return 0
