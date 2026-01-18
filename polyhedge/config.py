"""Environment configuration."""

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    anthropic_api_key: str
    cerebras_api_key: str
    brave_api_key: str
    token_company_api_key: Optional[str] = None  # Optional compression service

    # Gamma API settings
    gamma_api_base_url: str = "https://gamma-api.polymarket.com"

    # LLM settings
    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4096

    # Hedge settings
    default_budget: float = 100.0
    max_markets_in_bundle: int = 8

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
