from pathlib import Path

import pandas as pd
import pytest

from sales_lab.errors import InvalidInputError
from sales_lab.etl import SalesETL, to_cents


def test_to_cents_is_exact() -> None:
    assert to_cents("0.10") + to_cents("0.20") == 30
    assert to_cents("12.5") == 1250
    assert pd.isna(to_cents("abc"))


def test_missing_column_raises() -> None:
    raw = pd.DataFrame({"order_id": ["1"], "date": ["2026-01-01"]})
    with pytest.raises(InvalidInputError, match="Missing columns"):
        SalesETL().transform(raw)


def test_transform_keeps_only_valid_rows(sample_csv: Path) -> None:
    result = SalesETL().run(sample_csv)

    assert list(result.valid["order_id"]) == ["1", "2", "3"]
    assert list(result.valid["revenue_cents"]) == [2000, 10, 20]


def test_rejected_rows_have_reasons(sample_csv: Path) -> None:
    result = SalesETL().run(sample_csv)

    reasons = dict(zip(result.rejected["order_id"], result.rejected["reject_reason"], strict=True))
    assert reasons == {
        "2": "duplicate order_id",
        "4": "invalid date",
        "5": "invalid quantity",
    }


def test_category_and_whitespace_are_normalized(sample_csv: Path) -> None:
    result = SalesETL().run(sample_csv)

    row = result.valid.loc[result.valid["order_id"] == "3"].iloc[0]
    assert row["category"] == "Books"
    assert row["customer"] == "Petra"


def test_transform_does_not_modify_input(sample_csv: Path) -> None:
    etl = SalesETL()
    raw = etl.extract(sample_csv)
    before = raw.copy()

    etl.transform(raw)

    pd.testing.assert_frame_equal(raw, before)


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        SalesETL().extract(tmp_path / "missing.csv")


def test_invalid_row_does_not_block_valid_row_with_same_id(tmp_path: Path) -> None:
    path = tmp_path / "sales.csv"
    path.write_text(
        "order_id,date,customer,category,quantity,unit_price\n"
        "7,bad-date,Ana,Books,1,5.00\n"
        "7,2026-01-07,Ana,Books,1,5.00\n",
        encoding="utf-8",
    )

    result = SalesETL().run(path)

    assert list(result.valid["order_id"]) == ["7"]
    assert list(result.rejected["reject_reason"]) == ["invalid date"]
