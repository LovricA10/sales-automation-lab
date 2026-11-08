"""Shared fixtures: every test gets its own temporary database and CSV."""

from pathlib import Path

import pytest

from sales_lab.config import Settings
from sales_lab.service import SalesService, create_service

SAMPLE_CSV = """order_id,date,customer,category,quantity,unit_price
1,2026-01-01,Ana,Books,2,10.00
2,2026-01-02,Ivan,Home,1,0.10
2,2026-01-02,Ivan,Home,1,0.10
3,2026-01-03,Petra, books ,1,0.20
4,bad-date,Ana,Home,1,5.00
5,2026-01-05,Ana,Home,0,5.00
"""


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    path = tmp_path / "sales.csv"
    path.write_text(SAMPLE_CSV, encoding="utf-8")
    return path


@pytest.fixture
def settings(tmp_path: Path, sample_csv: Path) -> Settings:
    return Settings(
        input_path=sample_csv,
        db_path=tmp_path / "test.db",
        output_dir=tmp_path / "outputs",
    )


@pytest.fixture
def service(settings: Settings) -> SalesService:
    return create_service(settings)
