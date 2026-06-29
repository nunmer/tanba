"""Domain error types shared across apps.

Kept transport-agnostic: apps translate these into HTTP responses. Per DESIGN §9,
the dashboard maps NotFound/Forbidden to 404 to avoid leaking resource existence.
"""

from __future__ import annotations


class TanbaError(Exception):
    """Base class for expected domain errors."""


class NotFoundError(TanbaError):
    """Requested resource does not exist (or caller may not see it)."""


class ConflictError(TanbaError):
    """Uniqueness or state conflict (e.g. duplicate slug)."""


class AuthError(TanbaError):
    """Authentication failed or token invalid."""


class ForbiddenError(TanbaError):
    """Caller is authenticated but lacks access to the resource."""
