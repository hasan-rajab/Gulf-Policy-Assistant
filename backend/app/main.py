from contextlib import asynccontextmanager
from pathlib import Path
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
                result = ingestor.ingest_bytes(path.name, path.read_bytes(), source_uri=f"approved://policies/{path.name}")
                logger.info("demo_document_ingested", **result)
            except Exception:
                logger.exception("demo_document_ingest_failed", filename=path.name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    _bootstrap_demo_documents()
    yield


app = FastAPI(
    title="Gulf Horizon Enterprise RAG API",
    version="1.0.0",
    description="Bilingual Arabic/English policy RAG prototype for a fictional GCC bank.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)
    try:
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
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
            "request_id": request.headers.get("x-request-id"),
        },
    )


app.include_router(router)
