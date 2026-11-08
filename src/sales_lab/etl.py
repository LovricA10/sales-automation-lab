"""Extract + Transform: read the raw CSV and turn it into a clean, validated DataFrame."""

import logging
import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from sales_lab.errors import InvalidInputError

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ("order_id", "date", "customer", "category", "quantity", "unit_price")
CLEAN_COLUMNS = [
    "order_id",
    "date",
    "customer",
    "category",
    "quantity",
    "unit_price_cents",
    "revenue_cents",
]


def to_cents(value: str) -> float:
    """'12.50' -> 1250. An invalid amount returns NaN so that transform can reject it.

    Parsed via Decimal rather than float so that '0.10' is exactly 10 cents.
    The return type is float because a pandas column with NaN values must be float;
    once bad rows are dropped, the column is converted to int64.
    """
    try:
        amount = Decimal(value)
    except InvalidOperation:
        return math.nan
    if not amount.is_finite():
        return math.nan
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class TransformResult:
    valid: pd.DataFrame
    rejected: pd.DataFrame


class SalesETL:
    def extract(self, path: Path) -> pd.DataFrame:
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")
        # Read everything as text and parse it ourselves, so we know exactly what is wrong.
        return pd.read_csv(path, dtype=str, keep_default_na=False)

    def transform(self, raw: pd.DataFrame) -> TransformResult:
        missing = set(REQUIRED_COLUMNS) - set(raw.columns)
        if missing:
            raise InvalidInputError(f"Missing columns: {sorted(missing)}")

        df = raw.loc[:, list(REQUIRED_COLUMNS)].copy()  # copy: never modify the caller's input
        for column in REQUIRED_COLUMNS:
            df[column] = df[column].astype(str).str.strip()
        df["category"] = df["category"].str.title()

        df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
        df["unit_price_cents"] = df["unit_price"].map(to_cents)

        rules: list[tuple[pd.Series, str]] = [
            (df["order_id"] == "", "missing order_id"),
            (df["date"].isna(), "invalid date"),
            (df["customer"] == "", "missing customer"),
            (df["category"] == "", "missing category"),
            (
                df["quantity"].isna() | (df["quantity"] <= 0) | (df["quantity"] % 1 != 0),
                "invalid quantity",
            ),
            (
                df["unit_price_cents"].isna() | (df["unit_price_cents"] < 0),
                "invalid unit_price",
            ),
        ]
        reason = pd.Series("", index=df.index)
        for mask, text in rules:
            reason = reason.mask(mask & (reason == ""), text)  # the first reason wins

        # Look for duplicates only among valid rows; the first occurrence is kept.
        valid_ids = df["order_id"].where(reason == "")
        duplicate = (reason == "") & valid_ids.duplicated(keep="first")
        reason = reason.mask(duplicate, "duplicate order_id")

        is_valid = reason == ""
        rejected = raw.loc[~is_valid].copy()
        rejected["reject_reason"] = reason[~is_valid]

        valid = df.loc[is_valid].copy()
        valid["date"] = valid["date"].dt.strftime("%Y-%m-%d")
        valid["quantity"] = valid["quantity"].astype("int64")
        valid["unit_price_cents"] = valid["unit_price_cents"].astype("int64")
        valid["revenue_cents"] = valid["quantity"] * valid["unit_price_cents"]
        valid = valid.loc[:, CLEAN_COLUMNS].sort_values("order_id").reset_index(drop=True)

        logger.info("Transform: %d valid, %d rejected rows", len(valid), len(rejected))
        return TransformResult(valid=valid, rejected=rejected.reset_index(drop=True))

    def run(self, path: Path) -> TransformResult:
        return self.transform(self.extract(path))
