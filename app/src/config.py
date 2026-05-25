from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # OpenRouter LLM
    openrouter_api_key: str
    openrouter_model: str = "openai/gpt-5-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Optional data source keys
    companies_house_api_key: str = ""

    # Operational settings
    job_ttl_hours: int = 24
    module_timeout_seconds: int = 90


@lru_cache
def get_settings() -> Settings:
    return Settings()
