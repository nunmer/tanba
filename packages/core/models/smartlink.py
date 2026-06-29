"""SmartLink — the permanent resource a physical medium points at.

`branch_id` (org-level vs branch-level links) and richer landing config arrive in later
milestones; Milestone A keeps the columns needed to resolve a tap end-to-end.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.core.models.base import Base, created_at_col, uuid_pk


class SmartLink(Base):
    __tablename__ = "smartlink"

    id: Mapped[uuid.UUID] = uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # nullable -> org-level link; set -> scoped to a branch (DESIGN §5)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("branch.id", ondelete="SET NULL"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    slug: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)
    # type: redirect | multi | landing
    type: Mapped[str] = mapped_column(String(20), default="redirect", nullable=False)
    landing_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = created_at_col()

    destinations: Mapped[list[Destination]] = relationship(
        back_populates="smartlink",
        cascade="all, delete-orphan",
        order_by="Destination.priority",
    )


from packages.core.models.destination import Destination  # noqa: E402  (resolve forward ref)
