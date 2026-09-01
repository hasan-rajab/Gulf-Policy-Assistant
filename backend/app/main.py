from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.dependencies import get_ingestion_service, get_vector_store

settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger()


def _bootstrap_demo_documents() -> None:
    if not settings.demo_mode or settings.vector_backend != "local":
        return
    store = get_vector_store()
    if store.count() > 0:
        return
    sample_dir = settings.sample_data_dir
    if not sample_dir.exists():
        logger.warning("demo_sample_dir_missing", path=str(sample_dir))
        return
    ingestor = get_ingestion_service()
    for path in sorted(sample_dir.iterdir()):
        if path.suffix.lower() in {".pdf", ".docx", ".txt", ".md"}:
            try:
                result = ingestor.ingest_bytes(
                    path.name,
                    path.read_bytes(),
                    source_uri=f"approved://policies/{path.name}",
                    visibility="public",
                )
                logger.info("demo_document_ingested", **result)
            except Exception:
                logger.exception("demo_document_ingest_failed", filename=path.name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    _bootstrap_demo_documents()
    yield


app = FastAPI(
    title="NEXUS Enterprise AI API",
    version="2.0.0",
    description=(
        "Bilingual enterprise RAG with retrieval-time authorization, hybrid "
        "reranking, auditable abstention, and approval-gated enterprise actions."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-User-Email"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    request.state.request_id = request_id
    structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)
    try:
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["referrer-policy"] = "no-referrer"
        return response
    finally:
        structlog.contextvars.clear_contextvars()


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    logger.exception("unhandled_exception", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "detail": "The service could not complete the request.",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


app.include_router(router)
