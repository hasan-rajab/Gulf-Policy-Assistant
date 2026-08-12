from hashlib import sha256
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

from app.core.config import Settings
from app.services.chunking import chunk_text
from app.services.document_loader import load_document
from app.services.embeddings import EmbeddingProvider
from app.stores.base import StoredChunk, VectorStore


class IngestionService:
    def __init__(self, settings: Settings, embedder: EmbeddingProvider, store: VectorStore):
        self.settings = settings
        self.embedder = embedder
        self.store = store

    def ingest_bytes(self, filename: str, data: bytes, source_uri: str | None = None) -> dict:
        max_bytes = self.settings.max_file_mb * 1024 * 1024
        if len(data) > max_bytes:
            raise ValueError(f"File exceeds {self.settings.max_file_mb} MB limit")

        pages = load_document(filename, data)
        digest = sha256(data).hexdigest()[:16]
        document_id = str(uuid5(NAMESPACE_URL, f"{filename}:{digest}"))
        title = Path(filename).stem.replace("_", " ").replace("-", " ").strip()

        all_chunks = []
        running_index = 0
        for page in pages:
            page_chunks = chunk_text(
                page.text,
                chunk_size=self.settings.chunk_size_chars,
                overlap=self.settings.chunk_overlap_chars,
                page=page.page,
            )
            for c in page_chunks:
                c.chunk_index = running_index
                running_index += 1
                all_chunks.append(c)

        if not all_chunks:
            raise ValueError("No extractable text found in document")

        vectors = self.embedder.embed_documents([(title, c.text) for c in all_chunks])
        stored = []
        for chunk, vector in zip(all_chunks, vectors, strict=True):
            chunk_id = str(uuid5(NAMESPACE_URL, f"{document_id}:{chunk.chunk_index}:{chunk.text[:80]}"))
            stored.append(
                StoredChunk(
                    id=chunk_id,
                    document_id=document_id,
                    title=title,
                    text=chunk.text,
                    embedding=vector,
                    chunk_index=chunk.chunk_index,
                    page=chunk.page,
                    language=chunk.language,
                    source_uri=source_uri or filename,
                    metadata={"sha256_16": digest},
                )
            )
        self.store.upsert(stored)
        return {
            "document_id": document_id,
            "title": title,
            "chunks_created": len(stored),
        }
