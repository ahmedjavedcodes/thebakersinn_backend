"""FastAPI dependencies: DB-backed auth guard for admin routes."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import InvalidTokenError, decode_token
from app.crud import user as user_crud
from app.db.session import get_db
from app.models.user import AdminUser, Role

_bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        email = decode_token(credentials.credentials, expected_type="access")
    except InvalidTokenError as exc:
        raise unauthorized from exc

    admin = await user_crud.get_by_email(db, email)
    if admin is None or not admin.is_active:
        raise unauthorized

    return admin


async def require_owner(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
    """Authorization guard: the caller must be an authenticated owner.

    Layered on top of get_current_admin — employees are authenticated fine,
    they just can't perform owner-only actions (deleting catalog records,
    managing users and invitations). Wrong role -> 403, per CLAUDE.md §6.
    """
    if admin.role != Role.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires the owner role.",
        )
    return admin
