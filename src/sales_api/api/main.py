"""App factory, exception handlers and health check.

Run with: uvicorn sales_api.api.main:create_app --factory --reload
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from sales_api.api.deps import SessionDep
from sales_api.api.routers import auth, orders, reports
from sales_api.config import ApiSettings, get_settings
from sales_api.db import build_engine, build_session_factory
from sales_api.errors import AuthenticationError, ConflictError, NotFoundError
from sales_lab.errors import InvalidInputError


def _error(status_code: int, message: str, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": message}, headers=headers)


async def not_found(_: Request, exc: Exception) -> JSONResponse:
    return _error(status.HTTP_404_NOT_FOUND, str(exc))


async def conflict(_: Request, exc: Exception) -> JSONResponse:
    return _error(status.HTTP_409_CONFLICT, str(exc))


async def unauthorized(_: Request, exc: Exception) -> JSONResponse:
    return _error(status.HTTP_401_UNAUTHORIZED, str(exc), {"WWW-Authenticate": "Bearer"})


async def bad_input(_: Request, exc: Exception) -> JSONResponse:
    return _error(status.HTTP_400_BAD_REQUEST, str(exc))


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    engine = build_engine(resolved.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()  # close pooled connections on shutdown

    app = FastAPI(title="Sales API", version="0.2.0", lifespan=lifespan)
    app.state.settings = resolved
    app.state.engine = engine
    app.state.session_factory = build_session_factory(engine)

    app.add_exception_handler(NotFoundError, not_found)
    app.add_exception_handler(ConflictError, conflict)
    app.add_exception_handler(AuthenticationError, unauthorized)
    app.add_exception_handler(InvalidInputError, bad_input)

    app.include_router(auth.router)
    app.include_router(orders.router)
    app.include_router(reports.router)

    @app.get("/health", tags=["health"])
    def health(session: SessionDep) -> dict[str, str]:
        session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}

    return app
