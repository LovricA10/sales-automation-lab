"""REST API (read-only): translates HTTP requests into service calls."""

from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sales_lab.config import Settings
from sales_lab.errors import CategoryNotFoundError
from sales_lab.models import CategorySummary, SalesSummary, format_cents
from sales_lab.service import SalesService, create_service

# ---------- Response DTOs (the API contract, separate from domain dataclasses) ----------


class SummaryOut(BaseModel):
    orders: int
    units: int
    categories: int
    revenue_cents: int
    revenue: str

    @classmethod
    def from_domain(cls, summary: SalesSummary) -> "SummaryOut":
        return cls(
            orders=summary.orders,
            units=summary.units,
            categories=summary.categories,
            revenue_cents=summary.revenue_cents,
            revenue=format_cents(summary.revenue_cents),
        )


class CategoryOut(BaseModel):
    category: str
    orders: int
    units: int
    revenue_cents: int
    revenue: str

    @classmethod
    def from_domain(cls, item: CategorySummary) -> "CategoryOut":
        return cls(
            category=item.category,
            orders=item.orders,
            units=item.units,
            revenue_cents=item.revenue_cents,
            revenue=format_cents(item.revenue_cents),
        )


# ---------- Dependency injection ----------


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_service(settings: Annotated[Settings, Depends(get_settings)]) -> SalesService:
    return create_service(settings)


ServiceDep = Annotated[SalesService, Depends(get_service)]

# ---------- Routes ----------

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/summary", response_model=SummaryOut)
def summary(service: ServiceDep) -> SummaryOut:
    return SummaryOut.from_domain(service.summary())


@router.get("/categories", response_model=list[CategoryOut])
def categories(service: ServiceDep) -> list[CategoryOut]:
    return [CategoryOut.from_domain(item) for item in service.categories()]


@router.get("/categories/{name}", response_model=CategoryOut)
def category(name: str, service: ServiceDep) -> CategoryOut:
    return CategoryOut.from_domain(service.category(name))


async def category_not_found(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


def create_app(settings: Settings | None = None) -> FastAPI:
    """App factory: a test can pass its own Settings with a temporary database."""
    app = FastAPI(title="Sales Automation Lab", version="0.1.0")
    app.state.settings = settings or Settings.from_env()
    app.include_router(router)
    app.add_exception_handler(CategoryNotFoundError, category_not_found)
    return app


app = create_app()  # uvicorn sales_lab.api:app --reload
