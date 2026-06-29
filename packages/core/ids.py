"""Short public code generation for SmartLinks.

Codes use Crockford-style base32 (no I/L/O/U to avoid ambiguity and accidental words),
giving ~1 billion combinations at length 6. Collision handling is the caller's job:
generate, attempt insert, retry on the unique-constraint violation.
"""

from __future__ import annotations

import secrets

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32
DEFAULT_CODE_LENGTH = 6


def generate_code(length: int = DEFAULT_CODE_LENGTH) -> str:
    """Return a cryptographically-random base32 code of the given length."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))
