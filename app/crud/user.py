"""CRUD for admin users. All queries live here (CLAUDE.md §7)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import AdminUser, Role


async def get_by_email(db: AsyncSession, email: str) -> AdminUser | None:
    result = await db.execute(select(AdminUser).where(AdminUser.email == email))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: int) -> AdminUser | None:
    return await db.get(AdminUser, user_id)


async def list_users(db: AsyncSession) -> list[AdminUser]:
    result = await db.execute(select(AdminUser).order_by(AdminUser.id))
    return list(result.scalars().all())


async def count_active_owners(db: AsyncSession, *, exclude_id: int | None = None) -> int:
    stmt = select(func.count()).where(AdminUser.role == Role.OWNER, AdminUser.is_active.is_(True))
    if exclude_id is not None:
        stmt = stmt.where(AdminUser.id != exclude_id)
    return int((await db.execute(stmt)).scalar_one())


async def create_user(db: AsyncSession, *, email: str, password: str, role: Role) -> AdminUser:
    user = AdminUser(email=email, hashed_password=hash_password(password), role=role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(
    db: AsyncSession,
    user: AdminUser,
    *,
    is_active: bool | None = None,
    role: Role | None = None,
) -> AdminUser:
    if is_active is not None:
        user.is_active = is_active
    if role is not None:
        user.role = role
    await db.commit()
    await db.refresh(user)
    return user


async def seed_admin(db: AsyncSession, *, email: str, password: str, role: Role = Role.OWNER) -> None:
    """Ensure the bootstrap account exists with the given role. Idempotent.

    If the row already exists it's left as-is except that its role is forced to
    ``role`` (default owner) — this promotes the pre-Week-3 single-admin row,
    and after the migration backfills everyone to 'employee' it's what keeps an
    owner in the system.
    """
    existing = await get_by_email(db, email)
    if existing is not None:
        if existing.role != role:
            existing.role = role
            await db.commit()
        return

    db.add(AdminUser(email=email, hashed_password=hash_password(password), role=role))
    await db.commit()
