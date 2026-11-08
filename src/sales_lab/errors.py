"""Application domain exceptions.

The layers below the API raise these; the API and CLI translate them into an
HTTP status or a terminal message, so the service needs to know nothing about HTTP.
"""


class SalesLabError(Exception):
    """Base application error: catch it to handle all of our errors."""


class InvalidInputError(SalesLabError):
    """The input file does not match the expected format."""


class CategoryNotFoundError(SalesLabError):
    """The requested category does not exist in the database."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Category '{name}' not found")
        self.name = name
