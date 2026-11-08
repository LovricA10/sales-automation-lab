"""Database access via SQLAlchemy. Repositories never commit: the service owns the transaction."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from sales_api.models import Category, Order, User
from sales_lab.models import CategorySummary


class CategoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_or_create(self, name: str) -> Category:
        category = self._session.scalar(select(Category).where(Category.name == name))
        if category is None:
            category = Category(name=name)
            self._session.add(category)
            self._session.flush()  # assign the ID now, without committing yet
        return category


class OrderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, order_id: int) -> Order | None:
        return self._session.get(Order, order_id, options=[selectinload(Order.category)])

    def get_by_external_id(self, external_id: str) -> Order | None:
        return self._session.scalar(select(Order).where(Order.external_id == external_id))

    def search(self, category: str | None, limit: int, offset: int) -> tuple[list[Order], int]:
        query = select(Order).options(selectinload(Order.category))  # avoids the N+1 query problem
        count_query = select(func.count()).select_from(Order)
        if category:
            condition = func.lower(Category.name) == category.lower()
            query = query.join(Order.category).where(condition)
            count_query = count_query.join(Order.category).where(condition)

        total = self._session.scalar(count_query) or 0
        page = query.order_by(Order.order_date.desc(), Order.id.desc()).limit(limit).offset(offset)
        return list(self._session.scalars(page)), total

    def add(self, order: Order) -> Order:
        self._session.add(order)
        self._session.flush()
        return order

    def delete(self, order: Order) -> None:
        self._session.delete(order)

    def revenue_by_category(self) -> list[CategorySummary]:
        revenue = func.sum(Order.quantity * Order.unit_price_cents)
        query = (
            select(Category.name, func.count(Order.id), func.sum(Order.quantity), revenue)
            .join(Order.category)
            .group_by(Category.name)
            .order_by(revenue.desc(), Category.name)
        )
        return [
            CategorySummary(
                category=name, orders=orders, units=int(units), revenue_cents=int(total)
            )
            for name, orders, units, total in self._session.execute(query)
        ]


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: int) -> User | None:
        return self._session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self._session.scalar(select(User).where(User.email == email))

    def add(self, user: User) -> User:
        self._session.add(user)
        self._session.flush()
        return user
