"""Load + queries: the only module that knows about SQL and SQLite."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd

from sales_lab.models import CategorySummary, SalesSummary

SCHEMA = """
CREATE TABLE IF NOT EXISTS sales (
    order_id         TEXT PRIMARY KEY,
    date             TEXT NOT NULL,
    customer         TEXT NOT NULL,
    category         TEXT NOT NULL,
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
    revenue_cents    INTEGER NOT NULL
)
"""

UPSERT = """
INSERT INTO sales (order_id, date, customer, category, quantity, unit_price_cents, revenue_cents)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (order_id) DO UPDATE SET
    date             = excluded.date,
    customer         = excluded.customer,
    category         = excluded.category,
    quantity         = excluded.quantity,
    unit_price_cents = excluded.unit_price_cents,
    revenue_cents    = excluded.revenue_cents
"""

CATEGORY_SELECT = """
SELECT category,
       COUNT(*)           AS orders,
       SUM(quantity)      AS units,
       SUM(revenue_cents) AS revenue_cents
FROM sales
"""

SaleRow = tuple[str, str, str, str, int, int, int]


class SalesRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row  # lets rows be read by column name
        return connection

    def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        # closing() closes the connection; "with connection" only commits or rolls back.
        with closing(self._connect()) as connection, connection:
            connection.execute(SCHEMA)

    def upsert(self, frame: pd.DataFrame) -> int:
        # Explicit conversion to Python types: sqlite3 cannot store numpy.int64.
        rows: list[SaleRow] = [
            (
                str(row.order_id),
                str(row.date),
                str(row.customer),
                str(row.category),
                int(row.quantity),
                int(row.unit_price_cents),
                int(row.revenue_cents),
            )
            for row in frame.itertuples(index=False)
        ]
        with closing(self._connect()) as connection, connection:
            connection.executemany(UPSERT, rows)
        return len(rows)

    def count(self) -> int:
        with closing(self._connect()) as connection:
            (total,) = connection.execute("SELECT COUNT(*) FROM sales").fetchone()
        return int(total)

    def summary(self) -> SalesSummary:
        query = """
            SELECT COUNT(*)                         AS orders,
                   COALESCE(SUM(quantity), 0)       AS units,
                   COALESCE(SUM(revenue_cents), 0)  AS revenue_cents,
                   COUNT(DISTINCT category)         AS categories
            FROM sales
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query).fetchone()
        return SalesSummary(
            orders=row["orders"],
            units=row["units"],
            revenue_cents=row["revenue_cents"],
            categories=row["categories"],
        )

    def revenue_by_category(self) -> list[CategorySummary]:
        query = CATEGORY_SELECT + " GROUP BY category ORDER BY revenue_cents DESC, category"
        with closing(self._connect()) as connection:
            rows = connection.execute(query).fetchall()
        return [_to_category(row) for row in rows]

    def category(self, name: str) -> CategorySummary | None:
        # The value is passed as a parameter (?), never via an f-string: prevents SQL injection.
        query = CATEGORY_SELECT + " WHERE lower(category) = lower(?) GROUP BY category"
        with closing(self._connect()) as connection:
            row = connection.execute(query, (name,)).fetchone()
        return _to_category(row) if row is not None else None


def _to_category(row: sqlite3.Row) -> CategorySummary:
    return CategorySummary(
        category=row["category"],
        orders=row["orders"],
        units=row["units"],
        revenue_cents=row["revenue_cents"],
    )
