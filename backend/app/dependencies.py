from functools import lru_cache

from app.core.config import get_settings
from app.services.actions import EnterpriseActionService
from app.services.actions_bigquery import BigQueryEnterpriseActionService
from app.services.audit import BigQueryAuditStore, SQLiteAuditStore
from app.services.conversations import ConversationStore
from app.services.embeddings import GeminiEmbeddingProvider, LocalHashEmbeddingProvider
from app.services.evaluation import EvaluationService
from app.services.generation import DemoGenerator, GeminiGenerator
from app.services.ingestion import IngestionService
from app.services.rag import RAGService
from app.stores.bigquery import BigQueryVectorStore
from app.stores.local import LocalVectorStore


@lru_cache
def get_vector_store():
    settings = get_settings()
    if settings.vector_backend == "bigquery":
        return BigQueryVectorStore(settings)
    return LocalVectorStore(settings.data_dir / "local_index.json")


@lru_cache
def get_embedder():
    settings = get_settings()
    if settings.demo_mode:
        return LocalHashEmbeddingProvider(settings.embedding_dimensions)
    return GeminiEmbeddingProvider(settings)


@lru_cache
def get_generator():
    settings = get_settings()
    if settings.demo_mode:
        return DemoGenerator()
    return GeminiGenerator(settings)


@lru_cache
def get_conversations():
    return ConversationStore()


@lru_cache
def get_audit_store():
    settings = get_settings()
    if settings.vector_backend == "bigquery":
        return BigQueryAuditStore(settings)
    return SQLiteAuditStore(settings.data_dir / "nexus_audit.db")


@lru_cache
def get_action_service():
    settings = get_settings()
    if settings.vector_backend == "bigquery":
        return BigQueryEnterpriseActionService(settings, get_audit_store())
    return EnterpriseActionService(
        settings.data_dir / "nexus_actions.db",
        get_audit_store(),
    )


@lru_cache
def get_ingestion_service():
    return IngestionService(get_settings(), get_embedder(), get_vector_store())


@lru_cache
def get_rag_service():
    return RAGService(
        get_settings(),
        get_embedder(),
        get_vector_store(),
        get_generator(),
        get_conversations(),
        get_audit_store(),
    )


@lru_cache
def get_evaluation_service():
    return EvaluationService(get_rag_service())
