"""Domain errors of the backend layer; main.py maps them to HTTP status codes."""


class AppError(Exception):
    """Base error of the API application."""


class NotFoundError(AppError):
    """The resource does not exist (404)."""


class ConflictError(AppError):
    """The resource already exists or conflicts with an existing one (409)."""


class AuthenticationError(AppError):
    """The user is not authenticated or the token is invalid (401)."""
