from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from sales_lab.api import create_app
from sales_lab.config import Settings
from sales_lab.service import create_service


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    create_service(settings).import_file(settings.input_path)
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_summary(client: TestClient) -> None:
    body = client.get("/summary").json()
    assert body["orders"] == 3
    assert body["revenue"] == "20.30"


def test_categories_sorted_by_revenue(client: TestClient) -> None:
    body = client.get("/categories").json()
    assert [item["category"] for item in body] == ["Books", "Home"]


def test_single_category(client: TestClient) -> None:
    response = client.get("/categories/books")
    assert response.status_code == 200
    assert response.json()["revenue_cents"] == 2020


def test_unknown_category_returns_404(client: TestClient) -> None:
    response = client.get("/categories/Toys")
    assert response.status_code == 404
    assert "Toys" in response.json()["detail"]
