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
from app.crud import invitation as invitation_crud
from app.crud import user as user_crud
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair
from app.schemas.invitation import InvitationAccept, InvitationPublicInfo, JoinRequestCreate

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


@router.post(
    "/join-requests",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request access to the admin panel (an owner must approve)",
)
async def request_to_join(payload: JoinRequestCreate, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    if await user_crud.get_by_email(db, payload.email) is None and (
        await invitation_crud.get_live_for_email(db, payload.email) is None
    ):
        await invitation_crud.create_request(db, email=payload.email)
    # Always report the same result — don't leak whether the email is known.
    return {"detail": "If the address is eligible, an owner will review the request."}


@router.get(
    "/invitations/{token}",
    response_model=InvitationPublicInfo,
    summary="Look up a pending invitation by its token",
)
async def get_invitation(token: str, db: AsyncSession = Depends(get_db)) -> InvitationPublicInfo:
    invitation = await invitation_crud.get_by_token(db, token)
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown invitation token")
    if not invitation.is_acceptable:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This invitation is no longer valid")
    return InvitationPublicInfo(
        email=invitation.email, role=invitation.role, expires_at=invitation.expires_at
    )


@router.post(
    "/invitations/{token}/accept",
    response_model=TokenPair,
    summary="Accept an invitation: set a password, get logged in",
)
async def accept_invitation(
    token: str, payload: InvitationAccept, db: AsyncSession = Depends(get_db)
) -> TokenPair:
    invitation = await invitation_crud.get_by_token(db, token)
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown invitation token")
    if not invitation.is_acceptable:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This invitation is no longer valid")
    if await user_crud.get_by_email(db, invitation.email) is not None:
        await invitation_crud.mark_accepted(db, invitation)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That email already has an account")

    user = await user_crud.create_user(
        db, email=invitation.email, password=payload.password, role=invitation.role
    )
    await invitation_crud.mark_accepted(db, invitation)
    return TokenPair(
        access_token=create_access_token(user.email),
        refresh_token=create_refresh_token(user.email),
    )
