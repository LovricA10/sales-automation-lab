from fastapi.testclient import TestClient

from tests.backend.helpers import PASSWORD


def test_register_returns_201(client: TestClient) -> None:
    response = client.post(
        "/auth/register", json={"email": "Ivan@Example.com", "password": PASSWORD}
    )

    assert response.status_code == 201
    assert response.json()["email"] == "ivan@example.com"
    assert "password" not in response.text


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    body = {"email": "ivan@example.com", "password": PASSWORD}
    client.post("/auth/register", json=body)

    assert client.post("/auth/register", json=body).status_code == 409


def test_short_password_returns_422(client: TestClient) -> None:
    response = client.post("/auth/register", json={"email": "a@b.hr", "password": "short"})
    assert response.status_code == 422


def test_wrong_password_returns_401(client: TestClient) -> None:
    client.post("/auth/register", json={"email": "ivan@example.com", "password": PASSWORD})

    response = client.post(
        "/auth/token", data={"username": "ivan@example.com", "password": "wrong-password"}
    )

    assert response.status_code == 401


def test_me_with_token(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/auth/me", headers=auth_headers)
    assert response.json()["email"] == "ana@example.com"


def test_invalid_token_returns_401(client: TestClient) -> None:
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401
