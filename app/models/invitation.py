"""EmployeeInvitation model.

One table backs both onboarding paths (CLAUDE.md §6):

- **Owner invites someone** — owner creates the row directly with
  ``status = pending`` and a random ``token``. The invitee opens the link,
  sets a password, and their account is created.
- **Someone requests to join** — a public endpoint creates the row with
  ``status = requested`` and no token. An owner approves it, which mints the
  token and moves it to ``status = pending``; from there it's the same as above.

``email`` is intentionally *not* unique — a single address may accumulate
revoked/expired rows over time. At most one row per email may be live
(``requested`` or ``pending``); the CRUD layer enforces that.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.models.user import ROLE_ENUM, Role


class InvitationStatus(enum.StrEnum):
    REQUESTED = "requested"  # self-serve request, awaiting owner approval
    PENDING = "pending"  # token issued, awaiting the invitee setting a password
    ACCEPTED = "accepted"  # account created from this invitation
    REVOKED = "revoked"  # cancelled by an owner


STATUS_ENUM = Enum(
    InvitationStatus,
    name="invitation_status",
    native_enum=False,
    length=20,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class EmployeeInvitation(TimestampMixin, Base):
    __tablename__ = "employee_invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[Role] = mapped_column(ROLE_ENUM, nullable=False, default=Role.EMPLOYEE)
    status: Mapped[InvitationStatus] = mapped_column(
        STATUS_ENUM, nullable=False, default=InvitationStatus.PENDING
    )
    token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    invited_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    @property
    def is_expired(self) -> bool:
        return (
            self.status == InvitationStatus.PENDING
            and self.expires_at is not None
            and self.expires_at < datetime.now(UTC)
        )

    @property
    def is_acceptable(self) -> bool:
        return self.status == InvitationStatus.PENDING and not self.is_expired

    def __repr__(self) -> str:  # pragma: no cover
        return f"EmployeeInvitation(id={self.id!r}, email={self.email!r}, status={self.status.value!r})"
