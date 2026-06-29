"""Password hashing (Argon2) and JWT issue/verify for the dashboard."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from packages.core.errors import AuthError
from packages.core.settings import get_settings

_ph = PasswordHasher()
_ALGORITHM = "HS256"

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def _now() -> datetime:
    return datetime.now(UTC)


def create_token(user_id: uuid.UUID, token_type: TokenType) -> str:
    settings = get_settings()
    ttl = settings.jwt_access_ttl if token_type == "access" else settings.jwt_refresh_ttl
    now = _now()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_token(token: str, expected_type: TokenType) -> uuid.UUID:
    """Return the subject user id, or raise AuthError if invalid/expired/wrong type."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise AuthError("invalid token") from exc

    if payload.get("type") != expected_type:
        raise AuthError("wrong token type")
    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise AuthError("malformed token subject") from exc
