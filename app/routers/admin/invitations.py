"""Admin invitation management — owner only (CLAUDE.md §6).

Covers both onboarding paths:
- POST /invitations           — owner invites a named person (-> pending + token)
- POST /invitations/{id}/approve — owner approves a self-serve join request
- GET  /invitations           — see everything, incl. 'requested' rows awaiting approval
- DELETE /invitations/{id}    — revoke a pending/requested invitation
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_owner
from app.crud import invitation as invitation_crud
from app.crud import user as user_crud
from app.db.session import get_db
from app.models.invitation import EmployeeInvitation, InvitationStatus
from app.models.user import AdminUser
from app.schemas.invitation import InvitationCreate, InvitationRead

router = APIRouter(prefix="/invitations", tags=["admin:invitations"], dependencies=[Depends(require_owner)])


@router.get("", response_model=list[InvitationRead], summary="List invitations and join requests")
async def list_invitations(db: AsyncSession = Depends(get_db)) -> list[EmployeeInvitation]:
    return await invitation_crud.list_all(db)


@router.post(
    "",
    response_model=InvitationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Invite someone to the admin panel",
)
async def create_invitation(
    payload: InvitationCreate,
    db: AsyncSession = Depends(get_db),
    current_owner: AdminUser = Depends(require_owner),
) -> EmployeeInvitation:
    if await user_crud.get_by_email(db, payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That email already has an account")
    if await invitation_crud.get_live_for_email(db, payload.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="There is already an open invitation for that email",
        )
    return await invitation_crud.create_invite(
        db, email=payload.email, role=payload.role, invited_by_id=current_owner.id
    )


@router.post(
    "/{invitation_id}/approve",
    response_model=InvitationRead,
    summary="Approve a self-serve join request (issues the acceptance token)",
)
async def approve_invitation(invitation_id: int, db: AsyncSession = Depends(get_db)) -> EmployeeInvitation:
    invitation = await invitation_crud.get_by_id(db, invitation_id)
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    if invitation.status != InvitationStatus.REQUESTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only a 'requested' invitation can be approved (this one is '{invitation.status.value}')",
        )
    if await user_crud.get_by_email(db, invitation.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That email already has an account")
    return await invitation_crud.approve_request(db, invitation)


@router.delete(
    "/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a pending or requested invitation",
)
async def revoke_invitation(invitation_id: int, db: AsyncSession = Depends(get_db)) -> None:
    invitation = await invitation_crud.get_by_id(db, invitation_id)
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    if invitation.status not in (InvitationStatus.REQUESTED, InvitationStatus.PENDING):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot revoke an invitation that is '{invitation.status.value}'",
        )
    await invitation_crud.revoke(db, invitation)
