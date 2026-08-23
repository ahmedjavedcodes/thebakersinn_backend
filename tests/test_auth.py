from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


async def test_login_success(client: AsyncClient, admin_token: str) -> None:
    resp = await client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_wrong_password(client: AsyncClient, admin_token: str) -> None:
    resp = await client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
    assert resp.status_code == 401


async def test_admin_route_requires_token(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/admin/categories",
        json={"name": "Cakes", "icon_url": "https://cdn.example.com/icons/cakes.png"},
    )
    assert resp.status_code == 401


async def test_refresh_issues_new_pair(client: AsyncClient, admin_token: str) -> None:
    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_refresh_rejects_access_token(client: AsyncClient, admin_token: str) -> None:
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": admin_token})
    assert resp.status_code == 401
