"""Business logic: ETL, database and reports. Knows nothing about HTTP or the terminal."""

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

import pandas as pd

from sales_lab.config import Settings
from sales_lab.errors import CategoryNotFoundError
from sales_lab.etl import SalesETL
from sales_lab.models import CategorySummary, ImportResult, SalesSummary, format_cents
from sales_lab.repository import SalesRepository

logger = logging.getLogger(__name__)


class SalesRepositoryPort(Protocol):
    """The contract the service expects from a repository (Python's "interface").

    SalesRepository satisfies it without inheriting from it, just by having the
    same methods. The same goes for FakeRepository in the tests.
    """

    def initialize(self) -> None: ...
    def upsert(self, frame: pd.DataFrame) -> int: ...
    def summary(self) -> SalesSummary: ...
    def revenue_by_category(self) -> list[CategorySummary]: ...
    def category(self, name: str) -> CategorySummary | None: ...


class SalesService:
    def __init__(self, etl: SalesETL, repository: SalesRepositoryPort) -> None:
        self._etl = etl
        self._repository = repository
        self._repository.initialize()

    def import_file(self, path: Path, rejected_path: Path | None = None) -> ImportResult:
        logger.info("Import start: %s", path)
        result = self._etl.run(path)
        loaded = self._repository.upsert(result.valid)

        if rejected_path is not None and not result.rejected.empty:
            rejected_path.parent.mkdir(parents=True, exist_ok=True)
            result.rejected.to_csv(rejected_path, index=False)

        outcome = ImportResult(
            read=len(result.valid) + len(result.rejected),
            loaded=loaded,
            rejected=len(result.rejected),
        )
        logger.info("Import finished: %s", outcome)
        return outcome

    def summary(self) -> SalesSummary:
        return self._repository.summary()

    def categories(self) -> list[CategorySummary]:
        return self._repository.revenue_by_category()

    def category(self, name: str) -> CategorySummary:
        found = self._repository.category(name)
        if found is None:
            raise CategoryNotFoundError(name)
        return found

    def write_report(self, output_path: Path) -> Path:
        rows = [
            {**asdict(item), "revenue": format_cents(item.revenue_cents)}
            for item in self.categories()
        ]
        columns = ["category", "orders", "units", "revenue_cents", "revenue"]
        report = pd.DataFrame(rows, columns=columns)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report.to_csv(output_path, index=False)
        logger.info("Report written: %s", output_path)
        return output_path


def create_service(settings: Settings) -> SalesService:
    """Composition root: the only place that knows which concrete classes are wired."""
    return SalesService(SalesETL(), SalesRepository(settings.db_path))
