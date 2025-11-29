"""
Configuration management using Pydantic Settings.
Loads from environment variables and .env file.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys for providers (LiteLLM handles routing)
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")

    # Model defaults
    default_model: str = Field(default="gpt-5-mini", alias="DEFAULT_MODEL")
    default_model_list: list[str] = Field(
        default=["gpt-5-mini", "gemini-2.5-flash"],
        alias="DEFAULT_MODEL_LIST",
        description="Default models for multi-model comparison (minimum 2)",
    )
    default_temperature: float = Field(default=0.2, alias="DEFAULT_TEMPERATURE")

    # Server settings
    server_name: str = Field(default="Multi")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Retry and timeout configuration
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    model_timeout_seconds: float = Field(
        default=180.0, alias="MODEL_TIMEOUT_SECONDS", description="Timeout in seconds for individual model calls"
    )

    # File processing limits
    max_files_per_review: int = Field(
        default=100, alias="MAX_FILES_PER_REVIEW", description="Maximum number of files to include in a single code review"
    )
    max_file_size_kb: int = Field(default=50, alias="MAX_FILE_SIZE_KB", description="Maximum file size in KB for reading and processing")

    # Artifact logging
    artifacts_dir: str = Field(
        default="",
        alias="ARTIFACTS_DIR",
        description="Directory for artifact logging (relative to base_path). Empty = disabled.",
    )


# Global settings instance
settings = Settings()
