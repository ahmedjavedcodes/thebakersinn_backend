"""Role-based authorization + admin user management.

owner   -> full access
employee -> create/edit everything, but NOT delete and NOT user management
"""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import EMPLOYEE_EMAIL

# --- GET /admin/me (any authenticated admin) --------------------------------


async def test_me_returns_owner(client: AsyncClient, owner_headers: dict[str, str]) -> None:
    resp = await client.get("/api/v1/admin/me", headers=owner_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "owner@thebakersinn.com"
    assert body["role"] == "owner"
    assert body["is_active"] is True
    assert "hashed_password" not in body


async def test_me_returns_employee(client: AsyncClient, employee_headers: dict[str, str]) -> None:
    resp = await client.get("/api/v1/admin/me", headers=employee_headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "employee"


async def test_me_requires_a_token(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/admin/me")).status_code == 401


async def _make_category(client: AsyncClient, headers: dict[str, str]) -> int:
    resp = await client.post(
        "/api/v1/admin/categories",
        json={"name": "Cakes", "display_order": 0, "icon_url": "https://cdn.example.com/i.png"},
        headers=headers,
    )
    return resp.json()["id"]


async def _make_product(client: AsyncClient, headers: dict[str, str], category_id: int) -> int:
    resp = await client.post(
        "/api/v1/admin/products",
        json={"category_id": category_id, "name": "Choc Cake", "base_price": "2000.00"},
        headers=headers,
    )
    return resp.json()["id"]


# --- employees may create + edit ---------------------------------------------


async def test_employee_can_create_and_edit(client: AsyncClient, employee_headers: dict[str, str]) -> None:
    category_id = await _make_category(client, employee_headers)
    assert category_id

    resp = await client.patch(
        f"/api/v1/admin/categories/{category_id}",
        json={"description": "edited by an employee"},
        headers=employee_headers,
    )
    assert resp.status_code == 200


# --- employees may NOT delete ----------------------------------------------


async def test_employee_cannot_delete_category(
    client: AsyncClient, owner_headers: dict[str, str], employee_headers: dict[str, str]
) -> None:
    category_id = await _make_category(client, owner_headers)
    resp = await client.delete(f"/api/v1/admin/categories/{category_id}", headers=employee_headers)
    assert resp.status_code == 403


async def test_employee_cannot_delete_product(
    client: AsyncClient, owner_headers: dict[str, str], employee_headers: dict[str, str]
) -> None:
    category_id = await _make_category(client, owner_headers)
    product_id = await _make_product(client, owner_headers, category_id)
    resp = await client.delete(f"/api/v1/admin/products/{product_id}", headers=employee_headers)
    assert resp.status_code == 403


async def test_owner_can_delete(client: AsyncClient, owner_headers: dict[str, str]) -> None:
    category_id = await _make_category(client, owner_headers)
    product_id = await _make_product(client, owner_headers, category_id)
    del_product = await client.delete(f"/api/v1/admin/products/{product_id}", headers=owner_headers)
    del_category = await client.delete(f"/api/v1/admin/categories/{category_id}", headers=owner_headers)
    assert del_product.status_code == 204
    assert del_category.status_code == 204


# --- /admin/users is owner-only ------------------------------------------------


async def test_employee_cannot_view_users(client: AsyncClient, employee_headers: dict[str, str]) -> None:
    assert (await client.get("/api/v1/admin/users", headers=employee_headers)).status_code == 403


async def test_owner_lists_users_with_roles(
    client: AsyncClient, owner_headers: dict[str, str], employee_headers: dict[str, str]
) -> None:
    resp = await client.get("/api/v1/admin/users", headers=owner_headers)
    assert resp.status_code == 200
    by_email = {u["email"]: u["role"] for u in resp.json()}
    assert by_email["owner@thebakersinn.com"] == "owner"
    assert by_email[EMPLOYEE_EMAIL] == "employee"


async def test_employee_cannot_create_users(client: AsyncClient, employee_headers: dict[str, str]) -> None:
    resp = await client.post(
        "/api/v1/admin/users",
        json={"email": "x@thebakersinn.com", "password": "password123", "role": "employee"},
        headers=employee_headers,
    )
    assert resp.status_code == 403


async def test_owner_creates_employee_who_can_then_log_in(
    client: AsyncClient, owner_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/v1/admin/users",
        json={"email": "fresh@thebakersinn.com", "password": "password123"},
        headers=owner_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "employee"

    login = await client.post(
        "/api/v1/auth/login", json={"email": "fresh@thebakersinn.com", "password": "password123"}
    )
    assert login.status_code == 200


async def test_create_user_duplicate_email_conflicts(
    client: AsyncClient, owner_headers: dict[str, str], employee_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/v1/admin/users",
        json={"email": EMPLOYEE_EMAIL, "password": "password123"},
        headers=owner_headers,
    )
    assert resp.status_code == 409


# --- manage: activate/deactivate + change role -------------------------------


async def test_owner_deactivates_employee(
    client: AsyncClient, owner_headers: dict[str, str], employee_headers: dict[str, str]
) -> None:
    users = (await client.get("/api/v1/admin/users", headers=owner_headers)).json()
    emp_id = next(u["id"] for u in users if u["email"] == EMPLOYEE_EMAIL)

    resp = await client.patch(
        f"/api/v1/admin/users/{emp_id}", json={"is_active": False}, headers=owner_headers
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # the now-deactivated employee's token no longer works
    assert (await client.get("/api/v1/admin/users", headers=employee_headers)).status_code == 401


async def test_owner_promotes_employee_to_owner(
    client: AsyncClient, owner_headers: dict[str, str], employee_headers: dict[str, str]
) -> None:
    users = (await client.get("/api/v1/admin/users", headers=owner_headers)).json()
    emp_id = next(u["id"] for u in users if u["email"] == EMPLOYEE_EMAIL)

    resp = await client.patch(f"/api/v1/admin/users/{emp_id}", json={"role": "owner"}, headers=owner_headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "owner"

    # promoted employee can now delete
    category_id = await _make_category(client, owner_headers)
    assert (
        await client.delete(f"/api/v1/admin/categories/{category_id}", headers=employee_headers)
    ).status_code == 204


async def test_owner_cannot_demote_last_owner(client: AsyncClient, owner_headers: dict[str, str]) -> None:
    users = (await client.get("/api/v1/admin/users", headers=owner_headers)).json()
    owner_id = next(u["id"] for u in users if u["role"] == "owner")

    resp = await client.patch(
        f"/api/v1/admin/users/{owner_id}", json={"role": "employee"}, headers=owner_headers
    )
    assert resp.status_code == 409


async def test_owner_cannot_deactivate_self(
    client: AsyncClient, owner_headers: dict[str, str], employee_headers: dict[str, str]
) -> None:
    # a second owner exists, so "last owner" isn't the blocker here — self-lockout is
    users = (await client.get("/api/v1/admin/users", headers=owner_headers)).json()
    emp_id = next(u["id"] for u in users if u["email"] == EMPLOYEE_EMAIL)
    await client.patch(f"/api/v1/admin/users/{emp_id}", json={"role": "owner"}, headers=owner_headers)

    owner_id = next(u["id"] for u in users if u["email"] == "owner@thebakersinn.com")
    resp = await client.patch(
        f"/api/v1/admin/users/{owner_id}", json={"is_active": False}, headers=owner_headers
    )
    assert resp.status_code == 409
