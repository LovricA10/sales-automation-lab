"""Backend tests: real HTTP calls via TestClient against a real database.

By default each test gets its own SQLite file. Set SALES_API_TEST_DATABASE_URL to run against
an existing database (e.g. PostgreSQL in CI) whose schema was created by `alembic upgrade head`.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text

from sales_api.api.main import create_app
from sales_api.config import ApiSettings
from sales_api.models import Base
from tests.backend.helpers import PASSWORD

# A dedicated variable, not SALES_API_DATABASE_URL: these tests wipe every table.
EXTERNAL_DATABASE_URL = os.getenv("SALES_API_TEST_DATABASE_URL")


@pytest.fixture
def api_settings(tmp_path: Path) -> ApiSettings:
    return ApiSettings(
        database_url=EXTERNAL_DATABASE_URL or f"sqlite:///{tmp_path / 'api.db'}",
        jwt_secret=SecretStr("test-secret-with-at-least-32-chars!"),
        access_token_minutes=5,
    )


@pytest.fixture
def client(api_settings: ApiSettings) -> Iterator[TestClient]:
    app = create_app(api_settings)
    if EXTERNAL_DATABASE_URL:
        # Shared database: start every test from empty tables in the migrated schema.
        tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
        with app.state.engine.begin() as connection:
            connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    else:
        Base.metadata.create_all(app.state.engine)  # faster than Alembic in tests
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    client.post("/auth/register", json={"email": "ana@example.com", "password": PASSWORD})
    response = client.post(
        "/auth/token", data={"username": "ana@example.com", "password": PASSWORD}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
