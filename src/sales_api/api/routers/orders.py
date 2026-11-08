from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from sales_api.api.deps import OrderServiceDep, get_current_user
from sales_api.schemas import OrderIn, OrderOut, OrderPage, OrderUpdate

router = APIRouter(prefix="/orders", tags=["orders"])
auth_required = [Depends(get_current_user)]  # reads are public, writes require a token


@router.get("", response_model=OrderPage)
def list_orders(
    service: OrderServiceDep,
    category: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OrderPage:
    orders, total = service.search(category, limit, offset)
    return OrderPage(
        items=[OrderOut.from_model(order) for order in orders],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, service: OrderServiceDep) -> OrderOut:
    return OrderOut.from_model(service.get(order_id))


@router.post(
    "",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=auth_required,
)
def create_order(data: OrderIn, service: OrderServiceDep) -> OrderOut:
    return OrderOut.from_model(service.create(data))


@router.patch("/{order_id}", response_model=OrderOut, dependencies=auth_required)
def update_order(order_id: int, data: OrderUpdate, service: OrderServiceDep) -> OrderOut:
    return OrderOut.from_model(service.update(order_id, data))


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=auth_required)
def delete_order(order_id: int, service: OrderServiceDep) -> None:
    service.delete(order_id)
