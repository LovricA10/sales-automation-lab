"""Immutable DTOs that the service returns to the CLI and the API.

Money is always an integer number of cents. Floats are never used for money:
0.1 + 0.2 is not exactly 0.3 as a float, but in cents 10 + 20 = 30.
"""

from dataclasses import dataclass
from decimal import Decimal


def format_cents(cents: int) -> str:
    """Format cents as a readable amount, e.g. 1250 -> '12.50'."""
    return f"{Decimal(cents) / 100:.2f}"


@dataclass(frozen=True, slots=True)
class ImportResult:
    read: int
    loaded: int
    rejected: int


@dataclass(frozen=True, slots=True)
class SalesSummary:
    orders: int
    units: int
    revenue_cents: int
    categories: int


@dataclass(frozen=True, slots=True)
class CategorySummary:
    category: str
    orders: int
    units: int
    revenue_cents: int
