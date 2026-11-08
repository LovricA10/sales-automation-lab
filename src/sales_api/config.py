"""Settings from env variables."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SALES_API_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://sales:sales@localhost:5432/sales"
    jwt_secret: SecretStr  # no default: the app must not start without a secret
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30


@lru_cache
def get_settings() -> ApiSettings:
    # Values come from the environment, so mypy can't see the required argument.
    return ApiSettings()  # type: ignore[call-arg]
