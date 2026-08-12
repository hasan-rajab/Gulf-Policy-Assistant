from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


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


@dataclass
class SearchResult:
    chunk: StoredChunk
    score: float


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, chunks: list[StoredChunk]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, query_embedding: list[float], top_k: int) -> list[SearchResult]:
        raise NotImplementedError

    @abstractmethod
    def list_documents(self) -> list[dict]:
        raise NotImplementedError

    def count(self) -> int:
        return 0
