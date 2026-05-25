from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # OpenRouter LLM
    openrouter_api_key: str
    openrouter_model: str = "deepseek/deepseek-v4-flash"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Optional data source keys
    companies_house_api_key: str = ""

    # API key auth — comma-separated list of valid keys; leave blank to disable auth
    api_keys: str = ""

    # Operational settings
    job_ttl_hours: int = 24
    module_timeout_seconds: int = 90


@lru_cache
def get_settings() -> Settings:
    return Settings()
