"""Employee onboarding: owner-sent invitations and self-serve join requests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import EmployeeInvitation

# --- owner invites a named person -------------------------------------------


async def test_owner_invites_and_person_accepts(client: AsyncClient, owner_headers: dict[str, str]) -> None:
    resp = await client.post(
        "/api/v1/admin/invitations",
        json={"email": "newbaker@thebakersinn.com", "role": "employee"},
        headers=owner_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    token = body["token"]
    assert token

    info = await client.get(f"/api/v1/auth/invitations/{token}")
    assert info.status_code == 200
    assert info.json()["email"] == "newbaker@thebakersinn.com"
    assert info.json()["role"] == "employee"

    accept = await client.post(f"/api/v1/auth/invitations/{token}/accept", json={"password": "password123"})
    assert accept.status_code == 200
    assert accept.json()["access_token"]

    # account now exists and works
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "newbaker@thebakersinn.com", "password": "password123"},
    )
    assert login.status_code == 200


async def test_employee_cannot_send_invitations(
    client: AsyncClient, employee_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/v1/admin/invitations",
        json={"email": "x@thebakersinn.com"},
        headers=employee_headers,
    )
    assert resp.status_code == 403


async def test_invitation_cannot_be_accepted_twice(
    client: AsyncClient, owner_headers: dict[str, str]
) -> None:
    token = (
        await client.post(
            "/api/v1/admin/invitations",
            json={"email": "once@thebakersinn.com"},
            headers=owner_headers,
        )
    ).json()["token"]

    first = await client.post(f"/api/v1/auth/invitations/{token}/accept", json={"password": "password123"})
    assert first.status_code == 200

    second = await client.post(f"/api/v1/auth/invitations/{token}/accept", json={"password": "password123"})
    assert second.status_code in (404, 410)


async def test_duplicate_open_invitation_conflicts(
    client: AsyncClient, owner_headers: dict[str, str]
) -> None:
    await client.post(
        "/api/v1/admin/invitations", json={"email": "dup@thebakersinn.com"}, headers=owner_headers
    )
    resp = await client.post(
        "/api/v1/admin/invitations", json={"email": "dup@thebakersinn.com"}, headers=owner_headers
    )
    assert resp.status_code == 409


async def test_revoked_invitation_is_gone(client: AsyncClient, owner_headers: dict[str, str]) -> None:
    created = (
        await client.post(
            "/api/v1/admin/invitations",
            json={"email": "revoke-me@thebakersinn.com"},
            headers=owner_headers,
        )
    ).json()

    revoke = await client.delete(f"/api/v1/admin/invitations/{created['id']}", headers=owner_headers)
    assert revoke.status_code == 204

    info = await client.get(f"/api/v1/auth/invitations/{created['token']}")
    assert info.status_code in (404, 410)


async def test_expired_invitation_rejected(
    client: AsyncClient, owner_headers: dict[str, str], db_session: AsyncSession
) -> None:
    created = (
        await client.post(
            "/api/v1/admin/invitations",
            json={"email": "slowpoke@thebakersinn.com"},
            headers=owner_headers,
        )
    ).json()

    invitation = (
        await db_session.execute(select(EmployeeInvitation).where(EmployeeInvitation.id == created["id"]))
    ).scalar_one()
    invitation.expires_at = datetime.now(UTC) - timedelta(days=1)
    await db_session.commit()

    accept = await client.post(
        f"/api/v1/auth/invitations/{created['token']}/accept", json={"password": "password123"}
    )
    assert accept.status_code == 410


# --- self-serve join request, approved by an owner --------------------------


async def test_join_request_flow(client: AsyncClient, owner_headers: dict[str, str]) -> None:
    req = await client.post("/api/v1/auth/join-requests", json={"email": "hopeful@example.com"})
    assert req.status_code == 202

    listing = (await client.get("/api/v1/admin/invitations", headers=owner_headers)).json()
    pending_request = next(i for i in listing if i["email"] == "hopeful@example.com")
    assert pending_request["status"] == "requested"
    assert pending_request["token"] is None

    approve = await client.post(
        f"/api/v1/admin/invitations/{pending_request['id']}/approve", headers=owner_headers
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "pending"
    token = approve.json()["token"]
    assert token

    accept = await client.post(f"/api/v1/auth/invitations/{token}/accept", json={"password": "password123"})
    assert accept.status_code == 200


async def test_cannot_approve_a_non_requested_invitation(
    client: AsyncClient, owner_headers: dict[str, str]
) -> None:
    created = (
        await client.post(
            "/api/v1/admin/invitations",
            json={"email": "already-pending@thebakersinn.com"},
            headers=owner_headers,
        )
    ).json()

    resp = await client.post(f"/api/v1/admin/invitations/{created['id']}/approve", headers=owner_headers)
    assert resp.status_code == 409


async def test_accept_requires_min_password_length(
    client: AsyncClient, owner_headers: dict[str, str]
) -> None:
    token = (
        await client.post(
            "/api/v1/admin/invitations",
            json={"email": "shortpw@thebakersinn.com"},
            headers=owner_headers,
        )
    ).json()["token"]

    resp = await client.post(f"/api/v1/auth/invitations/{token}/accept", json={"password": "short"})
    assert resp.status_code == 422


async def test_unknown_token_is_404(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/auth/invitations/nope")).status_code == 404
