"""User and Membership — identity and org access."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from packages.core.models.base import Base, created_at_col, uuid_pk


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = created_at_col()


class Membership(Base):
    """Links a user to an organization with a role. A user may belong to many orgs."""

    __tablename__ = "membership"
    __table_args__ = (UniqueConstraint("user_id", "org_id", name="uq_membership_user_org"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # role: owner | admin | member
    role: Mapped[str] = mapped_column(String(20), default="owner", nullable=False)
    created_at: Mapped[datetime] = created_at_col()
