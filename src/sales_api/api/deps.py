"""Dependency injection: what each endpoint receives."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from sales_api.config import ApiSettings
from sales_api.models import User
from sales_api.services import AuthService, OrderService


def get_settings(request: Request) -> ApiSettings:
    settings: ApiSettings = request.app.state.settings
    return settings


def get_session(request: Request) -> Iterator[Session]:
    """One session per HTTP request; closed (and rolled back) after the response."""
    with request.app.state.session_factory() as session:
        yield session


SettingsDep = Annotated[ApiSettings, Depends(get_settings)]
SessionDep = Annotated[Session, Depends(get_session)]


def get_order_service(session: SessionDep) -> OrderService:
    return OrderService(session)


def get_auth_service(session: SessionDep, settings: SettingsDep) -> AuthService:
    return AuthService(session, settings)


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], auth: AuthServiceDep) -> User:
    return auth.current_user(token)


CurrentUser = Annotated[User, Depends(get_current_user)]
