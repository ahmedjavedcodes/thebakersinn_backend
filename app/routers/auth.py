"""POST /api/v1/auth/login — issues tokens for the single shared admin account.

Not nested under /admin since it's the one endpoint you call *without* a
token yet (CLAUDE.md §6).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.crud import user as user_crud
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair, summary="Log in with the admin email and password")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    admin = await user_crud.get_by_email(db, payload.email)
    if admin is None or not admin.is_active or not verify_password(payload.password, admin.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    return TokenPair(
        access_token=create_access_token(admin.email),
        refresh_token=create_refresh_token(admin.email),
    )


@router.post("/refresh", response_model=TokenPair, summary="Exchange a refresh token for a new token pair")
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    try:
        email = decode_token(payload.refresh_token, expected_type="refresh")
    except InvalidTokenError as exc:
        raise unauthorized from exc

    admin = await user_crud.get_by_email(db, email)
    if admin is None or not admin.is_active:
        raise unauthorized

    return TokenPair(
        access_token=create_access_token(admin.email),
        refresh_token=create_refresh_token(admin.email),
    )
