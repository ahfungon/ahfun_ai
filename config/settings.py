"""Application configuration using Pydantic settings."""
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql://dual_agent_user:dual_agent_pass@localhost:5432/dual_agent_chat",
        description="Database connection string (PostgreSQL only)"
    )
    
    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )
    
    # LLM API Configuration
    openclaw_api_key: str = Field(
        default="",
        description="OpenClaw API key for dialogue generation"
    )
    openclaw_api_url: str = Field(
        default="https://api.openclaw.example.com/v1",
        description="OpenClaw API endpoint"
    )
    deepseek_api_key: str = Field(
        default="",
        description="DeepSeek API key for summary generation"
    )
    deepseek_api_url: str = Field(
        default="https://api.deepseek.com/v1",
        description="DeepSeek API endpoint"
    )
    deepseek_model: str = Field(
        default="deepseek-chat",
        description="DeepSeek model name"
    )
    minimax_api_key: str = Field(
        default="",
        description="MiniMax API key for summary generation"
    )
    minimax_api_url: str = Field(
        default="https://api.minimax.chat/v1",
        description="MiniMax API endpoint"
    )
    minimax_model: str = Field(
        default="abab6.5-chat",
        description="MiniMax model name"
    )
    
    # Summary Configuration
    summary_threshold: int = Field(
        default=8000,
        description="Token count threshold to trigger summary"
    )
    closing_timeout: int = Field(
        default=300,
        description="Timeout in seconds for closing_pending state (default 5 minutes)"
    )
    
    # Retry Configuration
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed summary jobs"
    )
    retry_delays: str = Field(
        default="1,2,4",
        description="Comma-separated retry delays in seconds (exponential backoff)"
    )
    
    # Celery Configuration
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL"
    )
    celery_max_concurrent_tasks: int = Field(
        default=5,
        description="Maximum concurrent Celery tasks"
    )
    
    # API Configuration
    api_host: str = Field(
        default="0.0.0.0",
        description="API server host"
    )
    api_port: int = Field(
        default=8000,
        description="API server port"
    )
    
    @property
    def retry_delays_list(self) -> List[int]:
        """Parse retry delays string into list of integers."""
        return [int(d.strip()) for d in self.retry_delays.split(",")]


# Global settings instance
settings = Settings()
