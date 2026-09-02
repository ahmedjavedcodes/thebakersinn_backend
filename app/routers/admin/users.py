"""Admin user management — owner only (CLAUDE.md §6).

Employees never reach these routes: the router-level require_owner dependency
returns 403 for them.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_owner
from app.crud import user as user_crud
from app.db.session import get_db
from app.models.user import AdminUser, Role
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["admin:users"], dependencies=[Depends(require_owner)])


@router.get("", response_model=list[UserRead], summary="List all admin users and their roles")
async def list_users(db: AsyncSession = Depends(get_db)) -> list[AdminUser]:
    return await user_crud.list_users(db)


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an admin user",
)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> AdminUser:
    if await user_crud.get_by_email(db, payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
    try:
        return await user_crud.create_user(
            db, email=payload.email, password=payload.password, role=payload.role
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use") from exc


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    summary="Activate/deactivate a user or change their role",
)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_owner: AdminUser = Depends(require_owner),
) -> AdminUser:
    user = await user_crud.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    deactivating = payload.is_active is False and user.is_active
    demoting = payload.role is not None and payload.role != Role.OWNER and user.role == Role.OWNER

    if user.id == current_owner.id and (deactivating or demoting):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot deactivate or demote your own account.",
        )

    if (deactivating or demoting) and user.role == Role.OWNER:
        remaining = await user_crud.count_active_owners(db, exclude_id=user.id)
        if remaining == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This is the last active owner; promote another owner first.",
            )

    return await user_crud.update_user(db, user, is_active=payload.is_active, role=payload.role)
