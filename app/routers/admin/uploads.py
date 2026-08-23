"""Admin image upload endpoint."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.schemas.upload import UploadResponse
from app.services.storage import ALLOWED_CONTENT_TYPES, get_storage

router = APIRouter(prefix="/uploads", tags=["admin:uploads"])


@router.post(
    "/image",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a category icon or product image",
)
async def upload_image(file: UploadFile = File(...)) -> UploadResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        allowed = sorted(ALLOWED_CONTENT_TYPES)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported content type {file.content_type!r}. Allowed: {allowed}",
        )

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File exceeds the {settings.MAX_UPLOAD_MB}MB limit",
        )
    await file.seek(0)

    storage = get_storage()
    url = await storage.save(file)
    return UploadResponse(url=url)
