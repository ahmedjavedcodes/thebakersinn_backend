"""AdminUser model + Role.

D3 (auth model) was originally resolved as a single shared admin login. Week 3
reverses that: named accounts with an ``owner`` / ``employee`` role split
(CLAUDE.md §6). The env-seeded account is always the owner; further accounts
are created by an owner directly or through an invitation (see
``app.models.invitation``).

Roles:
- ``owner``    — full access, incl. deleting categories/products and managing users.
- ``employee`` — create and edit everything, but cannot delete or manage users.
"""

from __future__ import annotations

import enum

from sqlalchemy import Boolean, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Role(enum.StrEnum):
    OWNER = "owner"
    EMPLOYEE = "employee"


# native_enum=False -> stored as VARCHAR + CHECK constraint, so adding a role
# later is a no-op migration. values_callable makes the CHECK use the lowercase
# values ("owner"/"employee") rather than the member names.
ROLE_ENUM = Enum(
    Role,
    name="admin_user_role",
    native_enum=False,
    length=20,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class AdminUser(TimestampMixin, Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    role: Mapped[Role] = mapped_column(
        ROLE_ENUM,
        nullable=False,
        default=Role.EMPLOYEE,
        server_default=Role.EMPLOYEE.value,
    )

    @property
    def is_owner(self) -> bool:
        return self.role == Role.OWNER

    def __repr__(self) -> str:  # pragma: no cover
        return f"AdminUser(id={self.id!r}, email={self.email!r}, role={self.role.value!r})"
