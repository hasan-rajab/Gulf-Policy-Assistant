from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.config import get_settings
from app.core.security import create_access_token, current_user
from app.dependencies import (
    get_conversations,
    get_evaluation_service,
    get_ingestion_service,
    get_rag_service,
    get_vector_store,
)
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    DocumentInfo,
    EvaluationRequest,
    EvaluationResponse,
    IngestResponse,
    LoginRequest,
    TokenResponse,
)

router = APIRouter()


@router.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "demo_mode": settings.demo_mode,
        "vector_backend": settings.vector_backend,
        "generation_model": "demo-deterministic" if settings.demo_mode else settings.gemini_model,
    }


@router.post("/api/auth/login", response_model=TokenResponse)
def login(body: LoginRequest):
    settings = get_settings()
    if settings.auth_mode != "demo":
        raise HTTPException(status_code=400, detail="Application login is disabled; use enterprise identity/IAP")
    if body.email.lower() != settings.demo_user_email.lower() or body.password != settings.demo_user_password:
        raise HTTPException(status_code=401, detail="Invalid demo credentials")
    return TokenResponse(access_token=create_access_token(body.email.lower()), user_email=body.email.lower())


@router.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest, user: str = Depends(current_user)):
    try:
        return get_rag_service().answer(body.query, body.conversation_id, user, body.top_k)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/api/conversations/{conversation_id}")
def conversation(conversation_id: str, user: str = Depends(current_user)):
    try:
        return {"conversation_id": conversation_id, "messages": get_conversations().get(conversation_id, user)}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/api/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...), user: str = Depends(current_user)):
    try:
        data = await file.read()
        result = get_ingestion_service().ingest_bytes(file.filename or "document", data)
        return IngestResponse(**result, backend=get_settings().vector_backend)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/documents", response_model=list[DocumentInfo])
def documents(user: str = Depends(current_user)):
    return [DocumentInfo(**d) for d in get_vector_store().list_documents()]


@router.post("/api/evaluate", response_model=EvaluationResponse)
def evaluate(body: EvaluationRequest, user: str = Depends(current_user)):
    return EvaluationResponse(**get_evaluation_service().run(body.cases, user))
