"""Password hashing and JWT tokens. Never write your own cryptography."""

from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from sales_api.errors import AuthenticationError

_password_hash = PasswordHash.recommended()  # Argon2


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def create_access_token(subject: str, secret: str, algorithm: str, minutes: int) -> str:
    now = datetime.now(UTC)
    payload = {"sub": subject, "iat": now, "exp": now + timedelta(minutes=minutes)}
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str, secret: str, algorithm: str) -> str:
    """Return 'sub' (the user ID) or raise AuthenticationError."""
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.InvalidTokenError as exc:  # expired, bad signature, malformed...
        raise AuthenticationError("Invalid or expired token") from exc
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise AuthenticationError("Token has no subject")
    return subject
