import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile

from sales_api.api.deps import OrderServiceDep, get_current_user
from sales_api.schemas import CategoryRevenueOut, ImportOut

router = APIRouter(tags=["reports"])


@router.get("/reports/categories", response_model=list[CategoryRevenueOut])
def revenue_by_category(service: OrderServiceDep) -> list[CategoryRevenueOut]:
    return [
        CategoryRevenueOut(
            category=item.category,
            orders=item.orders,
            units=item.units,
            revenue_cents=item.revenue_cents,
        )
        for item in service.revenue_by_category()
    ]


@router.post("/imports", response_model=ImportOut, dependencies=[Depends(get_current_user)])
def import_csv(file: UploadFile, service: OrderServiceDep) -> ImportOut:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "upload.csv"
        path.write_bytes(file.file.read())
        result = service.import_csv(path)
    return ImportOut(read=result.read, loaded=result.loaded, rejected=result.rejected)
