"""CRUD for the single admin user."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import AdminUser


async def get_by_email(db: AsyncSession, email: str) -> AdminUser | None:
    result = await db.execute(select(AdminUser).where(AdminUser.email == email))
    return result.scalar_one_or_none()


async def seed_admin(db: AsyncSession, *, email: str, password: str) -> None:
    """Create the admin account if it doesn't exist yet. Idempotent."""
    existing = await get_by_email(db, email)
    if existing is not None:
        return

    admin = AdminUser(email=email, hashed_password=hash_password(password))
    db.add(admin)
    await db.commit()
