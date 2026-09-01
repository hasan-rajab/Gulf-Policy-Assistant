import json
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

    app_name: str = "NEXUS Enterprise AI"
    environment: str = "development"
    demo_mode: bool = True
    auth_mode: str = "demo"  # demo | iap

    jwt_secret: str = "replace-this-for-any-non-local-use"
    jwt_algorithm: str = "HS256"
    token_expiry_minutes: int = 480

    # Demo accounts model an employee and a knowledge administrator. Production
    # deployments should use IAP/enterprise identity and populate access profiles
    # from a trusted identity directory rather than request headers.
    demo_accounts_json: str = (
        '{"employee@gulfhorizon.local":{"password":"Demo123!","roles":["employee"],"departments":["general"]},'
        '"admin@gulfhorizon.local":{"password":"Admin123!","roles":["employee","knowledge_admin"],"departments":["general"]}}'
    )
    access_profiles_json: str = "{}"

    google_cloud_project: str | None = None
    google_cloud_location: str = "global"
    gemini_model: str = "gemini-3-flash-preview"
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768

    vector_backend: str = "local"  # local | bigquery
    bq_dataset: str = "enterprise_rag"
    bq_table: str = "policy_chunks"
    bq_audit_table: str = "audit_events"
    bq_actions_table: str = "action_requests"
    bq_location: str = "US"

    retrieval_top_k: int = 5
    retrieval_candidate_multiplier: int = 4
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

    @property
    def bq_audit_table_fqn(self) -> str:
        if not self.google_cloud_project:
            raise ValueError("GOOGLE_CLOUD_PROJECT is required for BigQuery mode")
        return f"{self.google_cloud_project}.{self.bq_dataset}.{self.bq_audit_table}"

    @property
    def bq_actions_table_fqn(self) -> str:
        if not self.google_cloud_project:
            raise ValueError("GOOGLE_CLOUD_PROJECT is required for BigQuery mode")
        return f"{self.google_cloud_project}.{self.bq_dataset}.{self.bq_actions_table}"

    @property
    def demo_accounts(self) -> dict[str, dict]:
        return {str(k).lower(): v for k, v in json.loads(self.demo_accounts_json).items()}

    @property
    def access_profiles(self) -> dict[str, dict]:
        return {str(k).lower(): v for k, v in json.loads(self.access_profiles_json).items()}

    def access_profile_for(self, email: str) -> dict:
        email_n = email.strip().lower()
        if self.auth_mode == "demo":
            return self.demo_accounts.get(email_n, {})
        return self.access_profiles.get(email_n, {})


@lru_cache
def get_settings() -> Settings:
    return Settings()
