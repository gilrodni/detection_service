from functools import lru_cache
from typing import Final

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or `.env`."""

    app_name: str = "GenAI Detection Service"
    environment: str = Field("local", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    version: str = "0.1.0"
    log_level: str = "INFO"

    openai_api_key: str = Field(
        ...,
        env="OPENAI_API_KEY",
    )
    openai_base_url: str = Field(..., env="OPENAI_BASE_URL")
    openai_model: str = Field("gpt-4.1", env="OPENAI_MODEL")
    openai_request_timeout: float = Field(8.0, env="OPENAI_REQUEST_TIMEOUT")

    audit_log_size: int = Field(500, env="AUDIT_LOG_SIZE")

    db_host: str = Field(..., env="DB_HOST")
    db_port_server: int = Field(..., env="DB_PORT_SERVER")
    db_port_client: int = Field(..., env="DB_PORT_CLIENT")
    db_user: str = Field(..., env="DB_USER")
    db_password: str = Field(..., env="DB_PASSWORD")
    db_name: str = Field(..., env="DB_NAME")
    db_driver: str = Field("psycopg", env="DB_DRIVER")
    database_url: str | None = Field(None, env="DATABASE_URL")

    detection_topics: dict[str, str] = Field(
        default_factory=lambda: {
            "health": "Anything related to healthcare, diagnosis, treatment, medical conditions, medications, or mental health.",
            "finance": "Discussions about banking, investing, trading, credit, insurance, or corporate finance decisions.",
            "legal": "Topics involving laws, regulations, contracts, intellectual property, compliance, or litigation.",
            "hr": "Conversations about hiring, firing, payroll, employee relations, or sensitive personnel data.",
        }
    )

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        port = self.db_port_server if self.environment == "dev" else self.db_port_client
        return (
            f"postgresql+{self.db_driver}://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{port}/{self.db_name}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


DEFAULT_SETTINGS: Final[Settings] = Settings()


@lru_cache()
def get_settings() -> Settings:
    return DEFAULT_SETTINGS
