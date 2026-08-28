"""GET /api/v1/admin/me — who is this token?

Any authenticated admin (owner or employee). The admin panel calls this on
load to decide which controls to show and to detect a revoked/deactivated
session (get_current_admin re-checks the row, so a disabled account 401s here).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_admin
from app.models.user import AdminUser
from app.schemas.user import UserRead

router = APIRouter(prefix="/me", tags=["admin:me"])


@router.get("", response_model=UserRead, summary="The currently authenticated admin user")
async def read_me(current: AdminUser = Depends(get_current_admin)) -> AdminUser:
    return current
