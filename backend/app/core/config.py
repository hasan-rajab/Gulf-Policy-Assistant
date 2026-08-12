from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Gulf Horizon Enterprise RAG"
    environment: str = "development"
    demo_mode: bool = True
    auth_mode: str = "demo"  # demo | iap

    jwt_secret: str = "replace-this-for-any-non-local-use"
    jwt_algorithm: str = "HS256"
    token_expiry_minutes: int = 480
    demo_user_email: str = "employee@gulfhorizon.local"
    demo_user_password: str = "Demo123!"

    google_cloud_project: str | None = None
    google_cloud_location: str = "global"
    gemini_model: str = "gemini-3-flash-preview"
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768

    vector_backend: str = "local"  # local | bigquery
    bq_dataset: str = "enterprise_rag"
    bq_table: str = "policy_chunks"
    bq_location: str = "US"

    retrieval_top_k: int = 5
    min_relevance_score: float = 0.20
    chunk_size_chars: int = 1400
    chunk_overlap_chars: int = 220
    max_file_mb: int = 15

    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"
    data_dir: Path = Field(default=Path("data"))
    sample_data_dir: Path = Field(default=Path("../sample_data"))

    @property
    def allowed_origins(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def bq_table_fqn(self) -> str:
        if not self.google_cloud_project:
            raise ValueError("GOOGLE_CLOUD_PROJECT is required for BigQuery mode")
        return f"{self.google_cloud_project}.{self.bq_dataset}.{self.bq_table}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
