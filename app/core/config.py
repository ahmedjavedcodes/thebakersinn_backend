"""Application settings, loaded from environment variables / .env.

Single source of truth for configuration. Nothing else in the app should
call os.environ directly — import `settings` from here instead.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Database ---
    DATABASE_URL: str

    # --- Auth ---
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Pepper: a secret mixed into every password *before* bcrypt. Unlike the
    # per-password salt (bcrypt generates one and stores it inside the hash),
    # the pepper lives only here / in a secrets manager and never touches the
    # database, so a leaked DB dump can't be brute-forced offline without it.
    # Rotating this value invalidates every existing password hash.
    PASSWORD_PEPPER: str

    # Single shared admin account, seeded on startup if it doesn't exist yet.
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # --- Image storage ---
    IMAGE_STORAGE: Literal["local", "s3", "cloudinary"] = "local"
    UPLOAD_DIR: str = "./static/uploads"
    MAX_UPLOAD_MB: int = 5

    # --- Misc ---
    ENVIRONMENT: Literal["development", "production", "test"] = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
