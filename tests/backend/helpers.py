"""Shared values for backend tests (conftest is not imported directly)."""

PASSWORD = "secret-password-123"


def order_payload(external_id: str = "A-1", **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "external_id": external_id,
        "order_date": "2026-03-01",
        "customer": "Ana",
        "category": "books",
        "quantity": 2,
        "unit_price_cents": 1250,
    }
    payload.update(overrides)
    return payload
