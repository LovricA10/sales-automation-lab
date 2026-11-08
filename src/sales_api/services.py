"""Business logic and transaction boundaries."""

import logging
from datetime import date
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sales_api.config import ApiSettings
from sales_api.errors import AuthenticationError, ConflictError, NotFoundError
from sales_api.models import Category, Order, User
from sales_api.repositories import CategoryRepository, OrderRepository, UserRepository
from sales_api.schemas import OrderIn, OrderUpdate, UserIn
from sales_api.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from sales_lab.etl import SalesETL
from sales_lab.models import CategorySummary, ImportResult

logger = logging.getLogger(__name__)


def normalize_category(name: str) -> str:
    """Same rule as in the ETL: ' books ' -> 'Books'."""
    return name.strip().title()


class OrderService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._categories = CategoryRepository(session)

    def get(self, order_id: int) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} not found")
        return order

    def search(self, category: str | None, limit: int, offset: int) -> tuple[list[Order], int]:
        return self._orders.search(category, limit, offset)

    def create(self, data: OrderIn) -> Order:
        if self._orders.get_by_external_id(data.external_id) is not None:
            raise ConflictError(f"Order '{data.external_id}' already exists")
        order = Order(
            external_id=data.external_id,
            order_date=data.order_date,
            customer=data.customer.strip(),
            category=self._categories.get_or_create(normalize_category(data.category)),
            quantity=data.quantity,
            unit_price_cents=data.unit_price_cents,
        )
        self._orders.add(order)
        self._commit()
        return order

    def update(self, order_id: int, data: OrderUpdate) -> Order:
        order = self.get(order_id)
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        if "category" in changes:
            order.category = self._categories.get_or_create(
                normalize_category(changes.pop("category"))
            )
        for field, value in changes.items():
            setattr(order, field, value)
        self._commit()
        return order

    def delete(self, order_id: int) -> None:
        self._orders.delete(self.get(order_id))
        self._commit()

    def revenue_by_category(self) -> list[CategorySummary]:
        return self._orders.revenue_by_category()

    def import_csv(self, path: Path) -> ImportResult:
        """Idempotent import: existing external_ids are updated, new ones are added."""
        result = SalesETL().run(path)
        categories: dict[str, Category] = {}

        for row in result.valid.itertuples(index=False):
            name = str(row.category)
            if name not in categories:
                categories[name] = self._categories.get_or_create(name)
            values = {
                "order_date": date.fromisoformat(str(row.date)),
                "customer": str(row.customer),
                "category": categories[name],
                "quantity": int(row.quantity),
                "unit_price_cents": int(row.unit_price_cents),
            }
            existing = self._orders.get_by_external_id(str(row.order_id))
            if existing is None:
                self._orders.add(Order(external_id=str(row.order_id), **values))
            else:
                for field, value in values.items():
                    setattr(existing, field, value)

        self._commit()  # the whole file is one transaction: all or nothing
        outcome = ImportResult(
            read=len(result.valid) + len(result.rejected),
            loaded=len(result.valid),
            rejected=len(result.rejected),
        )
        logger.info("CSV import: %s", outcome)
        return outcome

    def _commit(self) -> None:
        try:
            self._session.commit()
        except IntegrityError as exc:  # e.g. two concurrent requests with the same external_id
            self._session.rollback()
            raise ConflictError("Data violates a database constraint") from exc


class AuthService:
    def __init__(self, session: Session, settings: ApiSettings) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._settings = settings

    def register(self, data: UserIn) -> User:
        email = data.email.strip().lower()
        if self._users.get_by_email(email) is not None:
            raise ConflictError("A user with this email already exists")
        user = self._users.add(User(email=email, password_hash=hash_password(data.password)))
        self._session.commit()
        return user

    def authenticate(self, email: str, password: str) -> str:
        user = self._users.get_by_email(email.strip().lower())
        # Same message for an unknown email and a wrong password: don't reveal which accounts exist.
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("Incorrect email or password")
        return create_access_token(
            subject=str(user.id),
            secret=self._settings.jwt_secret.get_secret_value(),
            algorithm=self._settings.jwt_algorithm,
            minutes=self._settings.access_token_minutes,
        )

    def current_user(self, token: str) -> User:
        subject = decode_access_token(
            token, self._settings.jwt_secret.get_secret_value(), self._settings.jwt_algorithm
        )
        user = self._users.get(int(subject))
        if user is None:
            raise AuthenticationError("User no longer exists")
        return user
