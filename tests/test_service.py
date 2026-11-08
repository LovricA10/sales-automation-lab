from pathlib import Path

import pandas as pd
import pytest

from sales_lab.errors import CategoryNotFoundError
from sales_lab.etl import SalesETL
from sales_lab.models import CategorySummary, SalesSummary
from sales_lab.service import SalesService


def test_import_is_idempotent(service: SalesService, sample_csv: Path) -> None:
    first = service.import_file(sample_csv)
    second = service.import_file(sample_csv)

    assert first.loaded == second.loaded == 3
    assert service.summary().orders == 3  # re-importing did not duplicate rows


def test_summary_after_import(service: SalesService, sample_csv: Path) -> None:
    service.import_file(sample_csv)

    assert service.summary() == SalesSummary(orders=3, units=4, revenue_cents=2030, categories=2)


def test_summary_on_empty_database(service: SalesService) -> None:
    assert service.summary() == SalesSummary(orders=0, units=0, revenue_cents=0, categories=0)


def test_category_lookup_is_case_insensitive(service: SalesService, sample_csv: Path) -> None:
    service.import_file(sample_csv)

    assert service.category("books").revenue_cents == 2020


def test_unknown_category_raises(service: SalesService, sample_csv: Path) -> None:
    service.import_file(sample_csv)

    with pytest.raises(CategoryNotFoundError):
        service.category("Toys")


def test_rejected_rows_written_to_csv(
    service: SalesService, sample_csv: Path, tmp_path: Path
) -> None:
    rejected_path = tmp_path / "out" / "rejected.csv"

    result = service.import_file(sample_csv, rejected_path)

    assert result.rejected == 3
    assert len(pd.read_csv(rejected_path)) == 3


def test_write_report(service: SalesService, sample_csv: Path, tmp_path: Path) -> None:
    service.import_file(sample_csv)

    path = service.write_report(tmp_path / "report.csv")

    report = pd.read_csv(path, dtype={"revenue": str})
    assert list(report["category"]) == ["Books", "Home"]
    assert list(report["revenue"]) == ["20.20", "0.10"]


class FakeRepository:
    """Inherits nothing, yet still satisfies SalesRepositoryPort (Protocol)."""

    def __init__(self) -> None:
        self.saved: list[pd.DataFrame] = []

    def initialize(self) -> None:
        pass

    def upsert(self, frame: pd.DataFrame) -> int:
        self.saved.append(frame)
        return len(frame)

    def summary(self) -> SalesSummary:
        return SalesSummary(orders=0, units=0, revenue_cents=0, categories=0)

    def revenue_by_category(self) -> list[CategorySummary]:
        return []

    def category(self, name: str) -> CategorySummary | None:
        return None


def test_service_works_with_fake_repository(sample_csv: Path) -> None:
    fake = FakeRepository()
    service = SalesService(SalesETL(), fake)

    result = service.import_file(sample_csv)

    assert result.loaded == 3
    assert len(fake.saved) == 1
