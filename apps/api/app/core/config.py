from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_name: str = "WebAgentFlow API"
    env: str = "development"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS allowed origins - comma-separated list
    cors_allowed_origins: str = ""

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "web_agent_flow"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    redis_host: str = "localhost"
    redis_port: int = 6379

    # LLM provider settings
    llm_api_key: str = ""
    llm_base_url: str = "https://api.minimax.io/v1"
    llm_default_model: str = "MiniMax-M2.7"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096
    llm_timeout: int = 60

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @computed_field
    @property
    def sqlalchemy_database_uri(self) -> str:
        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


settings = Settings()
