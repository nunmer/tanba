"""Pure routing engine: predicate matching and destination resolution.

Everything here is side-effect free and ORM-free so resolution is deterministic,
exhaustively testable, and cacheable (DESIGN §4). I/O (DB, Redis, GeoIP) lives in
the apps; this package only transforms data.
"""

from packages.routing.context import RequestContext, build_context, detect_platform
from packages.routing.engine import resolve
from packages.routing.predicate import matches
from packages.routing.types import DestinationView, LinkView, Resolution

__all__ = [
    "RequestContext",
    "build_context",
    "detect_platform",
    "matches",
    "resolve",
    "DestinationView",
    "LinkView",
    "Resolution",
]
