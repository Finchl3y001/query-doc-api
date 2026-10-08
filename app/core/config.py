from functools import lru_cache
from fastapi import FastAPI, Depends
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, PostgresDsn

class Settings(BaseSettings):
    POSTGRES_USER = SecretStr
    POSTGRES_PASSWORD = SecretStr
    POSTGRES_DB = SecretStr
    SECRET_KEY: SecretStr
    REFRESH_SECRET_KEY: SecretStr
    MISTRAL_API_KEY: SecretStr
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SYNC_URL: PostgresDsn
    ASYNC_URL: PostgresDsn

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()