"""AdminUser model.

D3 (auth model) was resolved as: single shared admin login rather than
owner/employee roles. Still modelled as a table (not env-var credentials) so
the password can be rotated without a redeploy, and so a future move to
multiple accounts/roles is a column addition, not a rewrite. The single row
is seeded on startup from ADMIN_EMAIL / ADMIN_PASSWORD if it doesn't exist.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class AdminUser(TimestampMixin, Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"AdminUser(id={self.id!r}, email={self.email!r})"
