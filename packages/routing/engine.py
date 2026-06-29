"""resolve(): choose a destination for a link given a request context.

Pure and deterministic. A/B selection is sticky per visitor because the weighted pick
is seeded by `ctx.visitor_hash`, so a returning visitor keeps their variant without any
server-side session state (DESIGN §4).
"""

from __future__ import annotations

import hashlib

from packages.routing.context import RequestContext
from packages.routing.predicate import matches
from packages.routing.types import DestinationView, LinkView, Resolution

_LANDING_TYPES = {"landing", "multi"}


def _seed_fraction(seed: str, salt: str) -> float:
    """Deterministic float in [0, 1) from a seed string, salted per link to avoid
    correlating variants across different links for the same visitor."""
    digest = hashlib.sha256(f"{seed}|{salt}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / float(1 << 64)


def _weighted_pick(candidates: list[DestinationView], seed: str, salt: str) -> DestinationView:
    total = sum(max(d.weight, 0) for d in candidates)
    if total <= 0:
        return candidates[0]
    target = _seed_fraction(seed, salt) * total
    cumulative = 0.0
    for dest in candidates:
        cumulative += max(dest.weight, 0)
        if target < cumulative:
            return dest
    return candidates[-1]


def resolve(link: LinkView, ctx: RequestContext) -> Resolution:
    """Resolve a link to a redirect destination, a landing render, or not_found."""
    if not link.is_active:
        return Resolution(kind="not_found")

    if link.type in _LANDING_TYPES:
        return Resolution(kind="landing", link=link)

    candidates = [d for d in link.destinations if d.is_active and matches(d.match, ctx)]
    if not candidates:
        return Resolution(kind="not_found")

    best_priority = min(d.priority for d in candidates)
    top = [d for d in candidates if d.priority == best_priority]

    chosen = top[0] if len(top) == 1 else _weighted_pick(top, ctx.visitor_hash, salt=link.id)
    return Resolution(kind="redirect", destination=chosen)
