"""branch, physical_medium, subscription + smartlink.branch_id

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-29
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "branch",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Asia/Almaty"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organization.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_branch_org_id", "branch", ["org_id"])

    op.add_column("smartlink", sa.Column("branch_id", sa.Uuid(), nullable=True))
    op.create_index("ix_smartlink_branch_id", "smartlink", ["branch_id"])
    op.create_foreign_key(
        "fk_smartlink_branch_id", "smartlink", "branch", ["branch_id"], ["id"], ondelete="SET NULL"
    )

    op.create_table(
        "physical_medium",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("smartlink_id", sa.Uuid(), nullable=False),
        sa.Column("medium_type", sa.String(length=20), nullable=False),
        sa.Column("serial", sa.String(length=120), nullable=True),
        sa.Column("provisioned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["smartlink_id"], ["smartlink.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_physical_medium_smartlink_id", "physical_medium", ["smartlink_id"])

    op.create_table(
        "subscription",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("plan", sa.String(length=20), nullable=False, server_default="free"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_ref", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organization.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id"),
    )


def downgrade() -> None:
    op.drop_table("subscription")
    op.drop_table("physical_medium")
    op.drop_constraint("fk_smartlink_branch_id", "smartlink", type_="foreignkey")
    op.drop_index("ix_smartlink_branch_id", table_name="smartlink")
    op.drop_column("smartlink", "branch_id")
    op.drop_table("branch")
