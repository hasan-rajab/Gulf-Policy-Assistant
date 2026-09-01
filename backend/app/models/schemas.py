from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_email: str
    roles: list[str] = Field(default_factory=list)
    departments: list[str] = Field(default_factory=list)


class Source(BaseModel):
    source_id: str
    document_id: str
    title: str
    text: str
    source_uri: str | None = None
    page: int | None = None
    chunk_index: int
    language: str = "mixed"
    score: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sources: list[Source] = Field(default_factory=list)


class ChatRequest(BaseModel):
    query: str = Field(min_length=2, max_length=4000)
    conversation_id: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=12)


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    language: Literal["ar", "en", "mixed"]
    sources: list[Source]
    grounded: bool
    request_id: str
    latency_ms: int
    model: str
    retrieval_backend: str


class DocumentInfo(BaseModel):
    document_id: str
    title: str
    chunks: int
    source_uri: str | None = None
    language: str = "mixed"
    visibility: str = "public"


class IngestResponse(BaseModel):
    document_id: str
    title: str
    chunks_created: int
    backend: str
    visibility: str = "public"
    allowed_roles: list[str] = Field(default_factory=list)
    allowed_departments: list[str] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    cases: list[dict[str, Any]]


class EvaluationResponse(BaseModel):
    total_cases: int
    retrieval_hit_at_k: float
    citation_rate: float
    citation_source_integrity_rate: float = 1.0
    grounding_decision_accuracy: float
    language_match_rate: float
    grounded_keyword_coverage: float
    avg_latency_ms: float
    cases: list[dict[str, Any]]


class ActionRequest(BaseModel):
    action_name: Literal[
        "create_it_service_ticket",
        "request_hr_policy_review",
        "request_policy_exception",
    ]
    payload: dict[str, Any]
    idempotency_key: str | None = Field(default=None, max_length=128)


class ActionResponse(BaseModel):
    id: str
    requester: str
    action_name: str
    payload: dict[str, Any]
    status: Literal["pending_approval", "approved", "executed"]
    created_at: str
    approved_at: str | None = None
    approved_by: str | None = None
    executed_at: str | None = None
    result: dict[str, Any] | None = None
