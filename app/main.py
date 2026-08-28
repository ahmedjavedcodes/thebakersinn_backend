"""FastAPI app: router registration, CORS, lifespan."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.dependencies import get_current_admin
from app.crud import user as user_crud
from app.db.session import AsyncSessionLocal
from app.routers import auth
from app.routers.admin import categories as admin_categories
from app.routers.admin import invitations as admin_invitations
from app.routers.admin import products as admin_products
from app.routers.admin import uploads as admin_uploads
from app.routers.admin import users as admin_users
from app.routers.public import categories as public_categories
from app.routers.public import products as public_products


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    async with AsyncSessionLocal() as session:
        await user_crud.seed_admin(session, email=settings.ADMIN_EMAIL, password=settings.ADMIN_PASSWORD)
    yield


app = FastAPI(
    title="The Bakers Inn API",
    description="REST API for The Bakers Inn bakery — public storefront reads and admin panel management.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(public_categories.router)
api_router.include_router(public_products.router)
api_router.include_router(auth.router)

admin_router = APIRouter(prefix="/admin", dependencies=[Depends(get_current_admin)])
admin_router.include_router(admin_categories.router)
admin_router.include_router(admin_products.router)
admin_router.include_router(admin_uploads.router)
admin_router.include_router(admin_users.router)
admin_router.include_router(admin_invitations.router)
api_router.include_router(admin_router)

app.include_router(api_router)


@app.get("/health", tags=["health"], summary="Liveness check")
async def health() -> dict[str, str]:
    return {"status": "ok"}
