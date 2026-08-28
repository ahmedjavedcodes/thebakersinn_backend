"""Shared pytest fixtures: an isolated Postgres test database, an httpx
AsyncClient wired to the app, and a ready-to-use admin bearer token.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import create_access_token
from app.crud import user as user_crud
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import Role

TEST_DATABASE_URL = settings.DATABASE_URL.rsplit("/", 1)[0] + "/bakers_inn_test"

_engine = create_async_engine(TEST_DATABASE_URL)
_TestSessionLocal = async_sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)


async def _override_get_db() -> AsyncGenerator[AsyncSession]:
    async with _TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
async def _clean_database() -> AsyncGenerator[None]:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    async with _TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


ADMIN_EMAIL = "owner@thebakersinn.com"
ADMIN_PASSWORD = "test-password-123"
EMPLOYEE_EMAIL = "baker@thebakersinn.com"
EMPLOYEE_PASSWORD = "employee-password-123"


@pytest.fixture
async def admin_token(db_session: AsyncSession) -> str:
    """A logged-in OWNER — the default for existing CRUD tests."""
    await user_crud.seed_admin(db_session, email=ADMIN_EMAIL, password=ADMIN_PASSWORD, role=Role.OWNER)
    return create_access_token(ADMIN_EMAIL)


@pytest.fixture
def auth_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


# Owner-role aliases, for tests that contrast the two roles explicitly.
@pytest.fixture
async def owner_headers(auth_headers: dict[str, str]) -> dict[str, str]:
    return auth_headers


@pytest.fixture
async def employee_headers(db_session: AsyncSession) -> dict[str, str]:
    await user_crud.create_user(
        db_session, email=EMPLOYEE_EMAIL, password=EMPLOYEE_PASSWORD, role=Role.EMPLOYEE
    )
    return {"Authorization": f"Bearer {create_access_token(EMPLOYEE_EMAIL)}"}
