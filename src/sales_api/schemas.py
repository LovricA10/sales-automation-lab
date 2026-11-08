"""Pydantic DTOs: the API contract, kept separate from the SQLAlchemy models."""

from datetime import date

from pydantic import BaseModel, Field

from sales_api.models import Order

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class OrderIn(BaseModel):
    external_id: str = Field(min_length=1, max_length=50)
    order_date: date
    customer: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    quantity: int = Field(gt=0)
    unit_price_cents: int = Field(ge=0)


class OrderUpdate(BaseModel):
    """PATCH: every field is optional; only the fields sent are changed."""

    order_date: date | None = None
    customer: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    quantity: int | None = Field(default=None, gt=0)
    unit_price_cents: int | None = Field(default=None, ge=0)


class OrderOut(BaseModel):
    id: int
    external_id: str
    order_date: date
    customer: str
    category: str
    quantity: int
    unit_price_cents: int
    revenue_cents: int

    @classmethod
    def from_model(cls, order: Order) -> "OrderOut":
        return cls(
            id=order.id,
            external_id=order.external_id,
            order_date=order.order_date,
            customer=order.customer,
            category=order.category.name,
            quantity=order.quantity,
            unit_price_cents=order.unit_price_cents,
            revenue_cents=order.revenue_cents,
        )


class OrderPage(BaseModel):
    items: list[OrderOut]
    total: int
    limit: int
    offset: int


class CategoryRevenueOut(BaseModel):
    category: str
    orders: int
    units: int
    revenue_cents: int


class ImportOut(BaseModel):
    read: int
    loaded: int
    rejected: int


class UserIn(BaseModel):
    email: str = Field(max_length=254, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
