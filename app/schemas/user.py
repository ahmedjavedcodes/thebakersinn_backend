"""Admin user schemas — one class per operation (CLAUDE.md §7).

Never carries hashed_password out to a client.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import Role


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="User ID.", examples=[2])
    email: EmailStr = Field(..., description="Login email.", examples=["baker@thebakersinn.com"])
    role: Role = Field(..., description="'owner' or 'employee'.", examples=["employee"])
    is_active: bool = Field(
        ..., description="Inactive users cannot log in and their tokens stop working.", examples=[True]
    )
    created_at: datetime = Field(..., description="Creation timestamp (UTC).")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC).")


class UserCreate(BaseModel):
    email: EmailStr = Field(
        ..., description="Login email. Must be unique.", examples=["baker@thebakersinn.com"]
    )
    password: str = Field(
        ..., min_length=8, description="Initial password, at least 8 characters.", examples=["s3cret-pass"]
    )
    role: Role = Field(
        default=Role.EMPLOYEE,
        description="Role for the new account. Defaults to 'employee'.",
        examples=["employee"],
    )


class UserUpdate(BaseModel):
    """PATCH — activate/deactivate and/or change role. Both optional."""

    is_active: bool | None = Field(
        default=None, description="Set false to disable the account.", examples=[False]
    )
    role: Role | None = Field(default=None, description="New role.", examples=["owner"])
