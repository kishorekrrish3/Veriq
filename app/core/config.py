"""VERIQ Application Configuration.
Loaded from environment variables or .env file with safe defaults.
"""

from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App identity
    APP_NAME: str = "VERIQ"
    APP_ENV: Literal["development", "testing", "production"] = "development"
    TAGLINE: str = "Code is generated. Proof is earned."
    DEBUG: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Persistence & Storage
    DATA_DIR: str = "./data"
    DATABASE_URL: str = "sqlite:///./data/veriq.db"

    # AI Infrastructure - Nebius Token Factory
    NEBIUS_API_KEY: str = Field(default="", description="Nebius Token Factory API Key")
    NEBIUS_BASE_URL: str = Field(
        default="https://api.studio.nebius.ai/v1",
        description="OpenAI-compatible endpoint for Nebius Token Factory",
    )

    # NVIDIA Nemotron Models
    NEBIUS_MODEL_FAST: str = Field(
        default="nvidia/nemotron-mini-4b-instruct",
        description="Fast tier for quick planning and simple changes",
    )
    NEBIUS_MODEL_STANDARD: str = Field(
        default="nvidia/Llama-3.1-Nemotron-70B-Instruct-HF",
        description="Standard tier for main patch generation",
    )
    NEBIUS_MODEL_ESCALATION: str = Field(
        default="nvidia/nemotron-4-340b-instruct",
        description="Escalation tier for complex repairs and regressions",
    )

    # Tavily Research API
    TAVILY_API_KEY: str = Field(default="", description="Tavily API Key for primary search and extract")
    TAVILY_BASE_URL: str = "https://api.tavily.com"

    # Execution Flags
    ENABLE_LIVE_INFERENCE: bool = False
    ENABLE_LIVE_RESEARCH: bool = False

    # Safety & Resource Budgets
    MAX_REPAIR_ATTEMPTS: int = 1
    MAX_EXECUTION_SECONDS: int = 30
    MAX_PATCH_FILES: int = 10
    MAX_PATCH_BYTES: int = 50000

    # Sandbox Isolation
    SANDBOX_DOCKER_IMAGE: str = "veriq-sandbox:latest"
    ALLOW_FALLBACK_SANDBOX: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_live_inference_configured(self) -> bool:
        return bool(self.NEBIUS_API_KEY.strip() and self.ENABLE_LIVE_INFERENCE)

    @property
    def is_live_research_configured(self) -> bool:
        return bool(self.TAVILY_API_KEY.strip() and self.ENABLE_LIVE_RESEARCH)

    @property
    def data_path(self) -> Path:
        p = Path(self.DATA_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
