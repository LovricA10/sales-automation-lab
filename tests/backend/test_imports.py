from pathlib import Path

from fastapi.testclient import TestClient


def upload(client: TestClient, path: Path, headers: dict[str, str]) -> dict[str, int]:
    with path.open("rb") as file:
        response = client.post(
            "/imports", files={"file": ("sales.csv", file, "text/csv")}, headers=headers
        )
    assert response.status_code == 200
    result: dict[str, int] = response.json()
    return result


def test_import_is_idempotent(
    client: TestClient, auth_headers: dict[str, str], sample_csv: Path
) -> None:
    first = upload(client, sample_csv, auth_headers)
    upload(client, sample_csv, auth_headers)

    assert first == {"read": 6, "loaded": 3, "rejected": 3}
    assert client.get("/orders").json()["total"] == 3


def test_report_after_import(
    client: TestClient, auth_headers: dict[str, str], sample_csv: Path
) -> None:
    upload(client, sample_csv, auth_headers)

    report = client.get("/reports/categories").json()

    assert [(row["category"], row["revenue_cents"]) for row in report] == [
        ("Books", 2020),
        ("Home", 10),
    ]


def test_import_with_wrong_columns_returns_400(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("id,amount\n1,10\n", encoding="utf-8")

    with bad.open("rb") as file:
        response = client.post(
            "/imports", files={"file": ("bad.csv", file, "text/csv")}, headers=auth_headers
        )

    assert response.status_code == 400


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok", "database": "ok"}
