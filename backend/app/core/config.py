from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["local", "development", "staging", "production"] = "local"
    app_name: str = "Smart Merchant"
    database_url: str
    redis_url: str
    jwt_secret: str
    jwt_access_ttl: int = 900
    jwt_refresh_ttl: int = 2_592_000
    log_level: str = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = []
    bootstrap_key: str

    @field_validator("cors_origins", mode="before")
    @classmethod
    def origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def secure_environment(self) -> "Settings":
        if not self.database_url.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use PostgreSQL with psycopg")
        if self.jwt_access_ttl < 60 or self.jwt_refresh_ttl <= self.jwt_access_ttl:
            raise ValueError("Invalid token TTL")
        if self.app_env in {"staging", "production"}:
            if len(self.jwt_secret) < 32 or len(self.bootstrap_key) < 32:
                raise ValueError("Production and staging secrets must be at least 32 characters")
            if "*" in self.cors_origins or not self.cors_origins:
                raise ValueError("Explicit CORS_ORIGINS required")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
