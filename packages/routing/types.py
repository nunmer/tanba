"""Immutable, JSON-serializable value types used by the routing engine.

These mirror the persisted SmartLink/Destination but carry no ORM machinery, so a
resolved link can be cached as plain JSON and resolution stays a pure function.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ResolutionKind = Literal["redirect", "landing", "not_found"]


@dataclass(frozen=True, slots=True)
class DestinationView:
    id: str
    url: str
    kind: str
    priority: int
    weight: int
    match: dict[str, Any] | None
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class LinkView:
    id: str
    org_id: str
    code: str
    slug: str | None
    type: str  # redirect | multi | landing
    is_active: bool
    landing_config: dict[str, Any] = field(default_factory=dict)
    destinations: tuple[DestinationView, ...] = ()


@dataclass(frozen=True, slots=True)
class Resolution:
    kind: ResolutionKind
    destination: DestinationView | None = None
    link: LinkView | None = None

    @property
    def is_redirect(self) -> bool:
        return self.kind == "redirect"
