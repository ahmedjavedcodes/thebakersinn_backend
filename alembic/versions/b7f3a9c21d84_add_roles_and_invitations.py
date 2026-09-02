"""add roles and employee invitations

Revision ID: b7f3a9c21d84
Revises: 306444d30551
Create Date: 2026-08-28 00:00:00.000000

Week 3 (CLAUDE.md §6): admin_users gains a `role` column ('owner' | 'employee')
and a new `employee_invitations` table backs both onboarding paths (owner
invites, and self-serve join requests that an owner approves).

Existing admin_users rows are backfilled to 'employee' by the column's
server_default; the application's startup seed then promotes the configured
ADMIN_EMAIL account back to 'owner'.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7f3a9c21d84"
down_revision: str | Sequence[str] | None = "306444d30551"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ROLE_VALUES = ("owner", "employee")
_STATUS_VALUES = ("requested", "pending", "accepted", "revoked")


def upgrade() -> None:
    role_enum = sa.Enum(*_ROLE_VALUES, name="admin_user_role", native_enum=False, length=20)
    status_enum = sa.Enum(*_STATUS_VALUES, name="invitation_status", native_enum=False, length=20)

    op.add_column(
        "admin_users",
        sa.Column("role", role_enum, nullable=False, server_default="employee"),
    )

    op.create_table(
        "employee_invitations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", role_enum, nullable=False, server_default="employee"),
        sa.Column("status", status_enum, nullable=False, server_default="pending"),
        sa.Column("token", sa.String(length=64), nullable=True),
        sa.Column("invited_by_id", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["invited_by_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(
        op.f("ix_employee_invitations_email"), "employee_invitations", ["email"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_employee_invitations_email"), table_name="employee_invitations")
    op.drop_table("employee_invitations")
    op.drop_column("admin_users", "role")
