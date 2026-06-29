"""Destination — a routing target plus the predicate under which it applies.

The set of a SmartLink's Destinations *is* its routing table (DESIGN §4). Milestone A
stores `match`/`priority`/`weight` but resolution only uses the highest-priority active
row; the full predicate engine lands in Milestone B.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.core.models.base import Base, uuid_pk

if TYPE_CHECKING:
    from packages.core.models.smartlink import SmartLink

DESTINATION_KINDS = (
    "review_2gis",
    "google_maps",
    "apple_maps",
    "yandex_maps",
    "instagram",
    "whatsapp",
    "telegram",
    "url",
)


class Destination(Base):
    __tablename__ = "destination"

    id: Mapped[uuid.UUID] = uuid_pk()
    smartlink_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("smartlink.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="url", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)  # lower wins
    weight: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # A/B within a priority
    # match: jsonb predicate; null = always matches
    match: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    smartlink: Mapped[SmartLink] = relationship(back_populates="destinations")
