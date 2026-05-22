from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite+aiosqlite:///./resume_ai.db"

    # LLM
    llm_provider: str = "groq"  # "groq" or "gemini"
    llm_model: str = "llama-3.3-70b-versatile"
    groq_api_key: str = ""
    gemini_api_key: str = ""

    # Storage
    storage_path: str = "./uploads"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_llm_provider():
    """Factory that returns the configured LLM provider."""
    settings = get_settings()
    if settings.llm_provider == "groq":
        from app.llm.groq import GroqProvider
        return GroqProvider()
    else:
        from app.llm.gemini import GeminiProvider
        return GeminiProvider()
