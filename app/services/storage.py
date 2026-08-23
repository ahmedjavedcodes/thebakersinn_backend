"""Image storage, behind a pluggable interface (Open Decision D2).

Ships with a local filesystem backend. Switching to Cloudinary/S3 later is a
matter of implementing ImageStorage and switching IMAGE_STORAGE in .env —
not a rewrite of the upload endpoint.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_EXTENSION_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class ImageStorage(ABC):
    @abstractmethod
    async def save(self, file: UploadFile) -> str:
        """Persist the uploaded file and return its public URL."""
        raise NotImplementedError


class LocalImageStorage(ImageStorage):
    def __init__(self, upload_dir: str) -> None:
        self._upload_dir = Path(upload_dir)

    async def save(self, file: UploadFile) -> str:
        content_type = file.content_type
        if content_type is None or content_type not in _EXTENSION_BY_CONTENT_TYPE:
            raise ValueError(f"Unsupported content type: {content_type!r}")
        extension = _EXTENSION_BY_CONTENT_TYPE[content_type]
        today = datetime.now(UTC)
        subdir = self._upload_dir / f"{today:%Y}" / f"{today:%m}"
        subdir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid.uuid4().hex}{extension}"
        destination = subdir / filename

        contents = await file.read()
        destination.write_bytes(contents)

        return f"/static/uploads/{today:%Y}/{today:%m}/{filename}"


def get_storage() -> ImageStorage:
    if settings.IMAGE_STORAGE == "local":
        return LocalImageStorage(settings.UPLOAD_DIR)
    raise NotImplementedError(
        f"IMAGE_STORAGE={settings.IMAGE_STORAGE!r} has no backend implemented yet. "
        "Implement ImageStorage for it in app/services/storage.py."
    )
