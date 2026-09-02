"""CRUD for employee invitations / join requests. All queries live here."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import EmployeeInvitation, InvitationStatus
from app.models.user import Role

TOKEN_TTL = timedelta(days=7)

_LIVE_STATUSES = (InvitationStatus.REQUESTED, InvitationStatus.PENDING)


def _new_token() -> str:
    return secrets.token_urlsafe(32)


def _expiry() -> datetime:
    return datetime.now(UTC) + TOKEN_TTL


async def get_by_id(db: AsyncSession, invitation_id: int) -> EmployeeInvitation | None:
    return await db.get(EmployeeInvitation, invitation_id)


async def get_by_token(db: AsyncSession, token: str) -> EmployeeInvitation | None:
    result = await db.execute(select(EmployeeInvitation).where(EmployeeInvitation.token == token))
    return result.scalar_one_or_none()


async def get_live_for_email(db: AsyncSession, email: str) -> EmployeeInvitation | None:
    """A 'requested' or 'pending' invitation for this email, if one exists."""
    result = await db.execute(
        select(EmployeeInvitation)
        .where(EmployeeInvitation.email == email, EmployeeInvitation.status.in_(_LIVE_STATUSES))
        .order_by(EmployeeInvitation.id.desc())
    )
    return result.scalars().first()


async def list_all(db: AsyncSession) -> list[EmployeeInvitation]:
    result = await db.execute(select(EmployeeInvitation).order_by(EmployeeInvitation.id.desc()))
    return list(result.scalars().all())


async def create_invite(
    db: AsyncSession, *, email: str, role: Role, invited_by_id: int
) -> EmployeeInvitation:
    """Owner-initiated: straight to 'pending' with a token."""
    invitation = EmployeeInvitation(
        email=email,
        role=role,
        status=InvitationStatus.PENDING,
        token=_new_token(),
        invited_by_id=invited_by_id,
        expires_at=_expiry(),
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    return invitation


async def create_request(db: AsyncSession, *, email: str) -> EmployeeInvitation:
    """Self-serve: 'requested', no token until an owner approves."""
    invitation = EmployeeInvitation(
        email=email,
        role=Role.EMPLOYEE,
        status=InvitationStatus.REQUESTED,
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    return invitation


async def approve_request(db: AsyncSession, invitation: EmployeeInvitation) -> EmployeeInvitation:
    invitation.status = InvitationStatus.PENDING
    invitation.token = _new_token()
    invitation.expires_at = _expiry()
    await db.commit()
    await db.refresh(invitation)
    return invitation


async def revoke(db: AsyncSession, invitation: EmployeeInvitation) -> EmployeeInvitation:
    invitation.status = InvitationStatus.REVOKED
    invitation.token = None
    await db.commit()
    await db.refresh(invitation)
    return invitation


async def mark_accepted(db: AsyncSession, invitation: EmployeeInvitation) -> EmployeeInvitation:
    invitation.status = InvitationStatus.ACCEPTED
    invitation.accepted_at = datetime.now(UTC)
    invitation.token = None
    await db.commit()
    await db.refresh(invitation)
    return invitation
