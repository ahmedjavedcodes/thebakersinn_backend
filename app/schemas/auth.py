"""Auth schemas — single shared admin login (see CLAUDE.md §6, D3)."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Admin account email.", examples=["owner@thebakersinn.com"])
    password: str = Field(..., min_length=1, description="Admin account password.", examples=["hunter2"])


class TokenPair(BaseModel):
    access_token: str = Field(..., description="Short-lived JWT for Authorization: Bearer.")
    refresh_token: str = Field(..., description="Long-lived JWT used to obtain a new access token.")
    token_type: str = Field(default="bearer", description="Always 'bearer'.", examples=["bearer"])


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="A previously issued refresh token.")
