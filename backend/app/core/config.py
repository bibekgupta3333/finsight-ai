"""
Application configuration using Pydantic Settings.

Manages environment variables and application settings.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        app_name: Application name
        debug: Debug mode flag
        api_v1_prefix: API version 1 prefix
        max_workers: Maximum number of async workers
        task_queue_max_size: Maximum task queue size
        rate_limit_per_minute: Rate limit per minute per client
        request_timeout: Request timeout in seconds
        batch_size: Batch processing size
    """

    # Application
    app_name: str = "FinSight AI"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000

    # Concurrency & Performance
    max_workers: int = 10
    task_queue_max_size: int = 1000
    rate_limit_per_minute: int = 100
    request_timeout: int = 60
    batch_size: int = 100

    # Redis (for sessions and caching)
    redis_url: Optional[str] = None  # Direct Redis URL (takes precedence)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    session_ttl_seconds: int = 3600  # 1 hour

    def get_redis_url(self) -> str:
        """
        Get Redis connection URL.

        Uses REDIS_URL env var if set, otherwise constructs from host/port/password.
        """
        # If REDIS_URL is explicitly set, use it
        if self.redis_url:
            return self.redis_url

        # Otherwise construct from individual components
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    cors_origins: list[str] = ["http://localhost:3000"]

    # LLM Configuration
    ollama_base_url: str = "http://localhost:11434"
    llm_model_name: str = "mistral:7b"
    llm_fast_model: str = "mistral:7b-instruct-q4_0"
    embedding_model_name: str = "bge-small-en-v1.5"
    max_context_tokens: int = 8192  # Mistral context window
    max_prompt_tokens: int = 1500  # Target prompt length
    llm_timeout: int = 60  # LLM request timeout in seconds
    llm_temperature_deterministic: float = 0.0  # For classification
    llm_temperature_creative: float = 0.7  # For explanations
    llm_top_p: float = 0.9  # Nucleus sampling
    llm_top_k: int = 40  # Top-k sampling
    embedding_dimension: int = 384  # bge-small embedding size

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings instance
    """
    return Settings()
