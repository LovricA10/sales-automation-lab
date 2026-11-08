from fastapi.testclient import TestClient

from tests.backend.helpers import order_payload


def test_create_requires_token(client: TestClient) -> None:
    assert client.post("/orders", json=order_payload()).status_code == 401


def test_create_and_get_order(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = client.post("/orders", json=order_payload(), headers=auth_headers)

    assert created.status_code == 201
    body = created.json()
    assert body["category"] == "Books"  # normalized from "books"
    assert body["revenue_cents"] == 2500

    fetched = client.get(f"/orders/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_duplicate_external_id_returns_409(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.post("/orders", json=order_payload(), headers=auth_headers)

    response = client.post("/orders", json=order_payload(), headers=auth_headers)

    assert response.status_code == 409


def test_invalid_quantity_returns_422(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/orders", json=order_payload(quantity=0), headers=auth_headers)
    assert response.status_code == 422


def test_unknown_order_returns_404(client: TestClient) -> None:
    assert client.get("/orders/999").status_code == 404


def test_list_with_filter_and_pagination(client: TestClient, auth_headers: dict[str, str]) -> None:
    for index in range(3):
        client.post("/orders", json=order_payload(f"B-{index}"), headers=auth_headers)
    client.post("/orders", json=order_payload("H-1", category="Home"), headers=auth_headers)

    page = client.get("/orders", params={"category": "books", "limit": 2}).json()

    assert page["total"] == 3
    assert len(page["items"]) == 2
    assert {item["category"] for item in page["items"]} == {"Books"}


def test_patch_changes_only_sent_fields(client: TestClient, auth_headers: dict[str, str]) -> None:
    order_id = client.post("/orders", json=order_payload(), headers=auth_headers).json()["id"]

    response = client.patch(
        f"/orders/{order_id}", json={"quantity": 5, "category": "home"}, headers=auth_headers
    )

    body = response.json()
    assert response.status_code == 200
    assert body["quantity"] == 5
    assert body["category"] == "Home"
    assert body["customer"] == "Ana"


def test_delete_returns_204_then_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    order_id = client.post("/orders", json=order_payload(), headers=auth_headers).json()["id"]

    assert client.delete(f"/orders/{order_id}", headers=auth_headers).status_code == 204
    assert client.get(f"/orders/{order_id}").status_code == 404
