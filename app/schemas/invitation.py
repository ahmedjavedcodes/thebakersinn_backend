"""Employee invitation / join-request schemas (CLAUDE.md §6)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.invitation import InvitationStatus
from app.models.user import Role


class InvitationCreate(BaseModel):
    """Owner invites a specific person."""

    email: EmailStr = Field(..., description="Who to invite.", examples=["newbaker@thebakersinn.com"])
    role: Role = Field(
        default=Role.EMPLOYEE, description="Role they'll get on acceptance.", examples=["employee"]
    )


class JoinRequestCreate(BaseModel):
    """Public: someone asks to be added to the admin panel."""

    email: EmailStr = Field(
        ..., description="Email of the person requesting access.", examples=["hopeful@example.com"]
    )


class InvitationAccept(BaseModel):
    """Public: invitee sets their password and the account is created."""

    password: str = Field(
        ..., min_length=8, description="Chosen password, at least 8 characters.", examples=["s3cret-pass"]
    )


class InvitationRead(BaseModel):
    """Admin-facing view. Includes the raw token so an owner can share the link
    (there's no email delivery configured — see CLAUDE.md §6)."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Invitation ID.", examples=[5])
    email: EmailStr = Field(..., description="Invitee email.", examples=["newbaker@thebakersinn.com"])
    role: Role = Field(..., description="Role granted on acceptance.", examples=["employee"])
    status: InvitationStatus = Field(
        ..., description="requested | pending | accepted | revoked.", examples=["pending"]
    )
    token: str | None = Field(
        default=None,
        description="Acceptance token. Null while status is 'requested'.",
        examples=["k3y-Vd9..."],
    )
    invited_by_id: int | None = Field(
        default=None, description="ID of the owner who sent it; null for self-requests.", examples=[1]
    )
    expires_at: datetime | None = Field(default=None, description="When the token stops working (UTC).")
    accepted_at: datetime | None = Field(default=None, description="When the account was created (UTC).")
    is_expired: bool = Field(..., description="True if pending but past expires_at.", examples=[False])
    created_at: datetime = Field(..., description="Creation timestamp (UTC).")


class InvitationPublicInfo(BaseModel):
    """What GET /auth/invitations/{token} returns — enough to prefill the
    accept form, nothing sensitive."""

    email: EmailStr = Field(..., description="Email the invitation is for.", examples=["x@example.com"])
    role: Role = Field(..., description="Role that will be granted.", examples=["employee"])
    expires_at: datetime | None = Field(default=None, description="Token expiry (UTC).")
