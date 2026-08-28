"""Password hashing and JWT issuing/verification for the single admin login."""

from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# Direct bcrypt rather than passlib: passlib's CryptContext is unmaintained
# and breaks against bcrypt>=4.0 (it probes bcrypt.__about__, which no
# longer exists).

# Password storage = pepper -> bcrypt(salt + peppered value):
#   1. HMAC-SHA256(pepper, password) folds in the app-wide secret pepper and
#      collapses any-length input to a fixed 32 bytes, sidestepping bcrypt's
#      72-byte truncation. base64 keeps the value NUL-free text.
#   2. bcrypt.hashpw() then generates a fresh random salt per password and
#      embeds it (plus cost) in the returned "$2b$..." string.
# So every hash carries: a unique salt (in the hash) + the pepper (in env).


def _pepper(password: str) -> bytes:
    digest = hmac.new(
        settings.PASSWORD_PEPPER.encode("utf-8"),
        password.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pepper(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(_pepper(plain_password), hashed_password.encode("utf-8"))


def _create_token(subject: str, expires_delta: timedelta, token_type: Literal["access", "refresh"]) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return str(jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM))


def create_access_token(subject: str) -> str:
    return _create_token(subject, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def create_refresh_token(subject: str) -> str:
    return _create_token(subject, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), "refresh")


class InvalidTokenError(Exception):
    pass


def decode_token(token: str, expected_type: Literal["access", "refresh"]) -> str:
    """Returns the subject (email) if the token is valid and of the expected type."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"expected a {expected_type} token")

    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError("token missing subject")

    return str(subject)
