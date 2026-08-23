"""Upload response schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    url: str = Field(
        ..., description="Public URL of the uploaded image.", examples=["/static/uploads/2026/08/abc123.jpg"]
    )
