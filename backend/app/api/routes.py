from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.core.access import AccessContext
from app.core.config import get_settings
from app.core.security import create_access_token, current_principal, require_knowledge_admin
from app.dependencies import (
    get_action_service,
    get_audit_store,
    get_conversations,
    get_evaluation_service,
    get_ingestion_service,
    get_rag_service,
    get_vector_store,
)
from app.models.schemas import (
    ActionRequest,
    ActionResponse,
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


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _csv(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


@router.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "demo_mode": settings.demo_mode,
        "vector_backend": settings.vector_backend,
        "generation_model": "demo-deterministic" if settings.demo_mode else settings.gemini_model,
        "retrieval": "acl-scoped-hybrid-reranked",
    }


@router.post("/api/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request):
    settings = get_settings()
    if settings.auth_mode != "demo":
        raise HTTPException(status_code=400, detail="Application login is disabled; use enterprise identity/IAP")

    email = body.email.lower().strip()
    account = settings.demo_accounts.get(email)
    if account is None or body.password != account.get("password"):
        get_audit_store().record(
            actor=email or "unknown",
            action="login",
            resource=None,
            outcome="denied",
            request_id=_request_id(request),
            details={},
        )
        raise HTTPException(status_code=401, detail="Invalid demo credentials")

    principal = AccessContext.create(
        email,
        account.get("roles", ["employee"]),
        account.get("departments", []),
    )
    get_audit_store().record(
        actor=email,
        action="login",
        resource=None,
        outcome="success",
        request_id=_request_id(request),
        details={"roles": sorted(principal.roles), "departments": sorted(principal.departments)},
    )
    return TokenResponse(
        access_token=create_access_token(email),
        user_email=email,
        roles=sorted(principal.roles),
        departments=sorted(principal.departments),
    )


@router.post("/api/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    principal: AccessContext = Depends(current_principal),
):
    try:
        return get_rag_service().answer(body.query, body.conversation_id, principal, body.top_k)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/api/conversations/{conversation_id}")
def conversation(
    conversation_id: str,
    principal: AccessContext = Depends(current_principal),
):
    try:
        return {
            "conversation_id": conversation_id,
            "messages": get_conversations().get(conversation_id, principal.email),
        }
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/api/ingest", response_model=IngestResponse)
async def ingest(
    request: Request,
    file: UploadFile = File(...),
    visibility: str = Form(default="public"),
    allowed_roles: str = Form(default=""),
    allowed_departments: str = Form(default=""),
    principal: AccessContext = Depends(require_knowledge_admin),
):
    try:
        data = await file.read()
        result = get_ingestion_service().ingest_bytes(
            file.filename or "document",
            data,
            visibility=visibility,
            allowed_roles=_csv(allowed_roles),
            allowed_departments=_csv(allowed_departments),
        )
        get_audit_store().record(
            actor=principal.email,
            action="document_ingested",
            resource=result["document_id"],
            outcome="success",
            request_id=_request_id(request),
            details={
                "title": result["title"],
                "chunks": result["chunks_created"],
                "visibility": result["visibility"],
                "allowed_roles": result["allowed_roles"],
                "allowed_departments": result["allowed_departments"],
            },
        )
        return IngestResponse(**result, backend=get_settings().vector_backend)
    except ValueError as exc:
        get_audit_store().record(
            actor=principal.email,
            action="document_ingested",
            resource=file.filename,
            outcome="rejected",
            request_id=_request_id(request),
            details={"reason": str(exc)},
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/documents", response_model=list[DocumentInfo])
def documents(principal: AccessContext = Depends(current_principal)):
    return [
        DocumentInfo(**document)
        for document in get_vector_store().list_documents(access=principal)
    ]


@router.post("/api/evaluate", response_model=EvaluationResponse)
def evaluate(
    body: EvaluationRequest,
    request: Request,
    principal: AccessContext = Depends(require_knowledge_admin),
):
    result = get_evaluation_service().run(body.cases, principal)
    get_audit_store().record(
        actor=principal.email,
        action="evaluation_run",
        resource=None,
        outcome="completed",
        request_id=_request_id(request),
        details={
            "total_cases": result["total_cases"],
            "retrieval_hit_at_k": result["retrieval_hit_at_k"],
            "citation_source_integrity_rate": result["citation_source_integrity_rate"],
        },
    )
    return EvaluationResponse(**result)


@router.post("/api/actions/request", response_model=ActionResponse)
def request_action(
    body: ActionRequest,
    request: Request,
    principal: AccessContext = Depends(current_principal),
):
    try:
        return ActionResponse(
            **get_action_service().request(
                principal=principal,
                action_name=body.action_name,
                payload=body.payload,
                request_id=_request_id(request),
                idempotency_key=body.idempotency_key,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/actions/{action_id}/approve", response_model=ActionResponse)
def approve_action(
    action_id: str,
    request: Request,
    principal: AccessContext = Depends(require_knowledge_admin),
):
    try:
        return ActionResponse(
            **get_action_service().approve(action_id, principal, _request_id(request))
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Action request not found") from exc
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=409 if isinstance(exc, ValueError) else 403, detail=str(exc)) from exc


@router.post("/api/actions/{action_id}/execute", response_model=ActionResponse)
def execute_action(
    action_id: str,
    request: Request,
    principal: AccessContext = Depends(require_knowledge_admin),
):
    try:
        return ActionResponse(
            **get_action_service().execute(action_id, principal, _request_id(request))
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Action request not found") from exc
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=409 if isinstance(exc, ValueError) else 403, detail=str(exc)) from exc


@router.get("/api/actions/{action_id}", response_model=ActionResponse)
def get_action(
    action_id: str,
    principal: AccessContext = Depends(current_principal),
):
    try:
        return ActionResponse(**get_action_service().get(action_id, principal))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Action request not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/api/audit/verify")
def verify_audit_chain(principal: AccessContext = Depends(require_knowledge_admin)):
    store = get_audit_store()
    verifier = getattr(store, "verify_chain", None)
    if verifier is None:
        return {"backend": "bigquery", "chain_verification": "external-warehouse-validation-required"}
    return {"backend": "sqlite", "chain_valid": bool(verifier())}
