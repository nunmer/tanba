"""PhysicalMedium — optional inventory of provisioned tags/QRs pointing at a link.

Tanba is not an NFC store: a SmartLink is fully functional with zero media rows
(DESIGN §5). Media is metadata, never a dependency of routing.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from packages.core.models.base import Base, created_at_col, uuid_pk

MEDIUM_TYPES = ("nfc_card", "nfc_stand", "nfc_sticker", "qr_stand", "business_card")


class PhysicalMedium(Base):
    __tablename__ = "physical_medium"

    id: Mapped[uuid.UUID] = uuid_pk()
    smartlink_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("smartlink.id", ondelete="CASCADE"), nullable=False, index=True
    )
    medium_type: Mapped[str] = mapped_column(String(20), nullable=False)
    serial: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provisioned_at: Mapped[datetime] = created_at_col()
