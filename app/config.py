from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    admin_api_token: str = ""
    db_connect_timeout: int = 5
    db_statement_timeout_ms: int = 4000
    public_cache_seconds: int = 300
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
