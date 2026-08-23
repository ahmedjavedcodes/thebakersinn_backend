from __future__ import annotations

from httpx import AsyncClient


async def _create_category(client: AsyncClient, headers: dict[str, str], **overrides: object) -> dict:
    payload = {
        "name": "Cakes",
        "description": "Our signature cakes.",
        "display_order": 0,
        "icon_url": "https://cdn.example.com/icons/cakes.png",
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/admin/categories", json=payload, headers=headers)
    return resp


async def test_create_category_requires_icon_url(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    resp = await client.post(
        "/api/v1/admin/categories", json={"name": "Cakes", "display_order": 0}, headers=auth_headers
    )
    assert resp.status_code == 422


async def test_create_category_generates_slug(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    resp = await _create_category(client, auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == "cakes"
    assert body["is_active"] is True


async def test_duplicate_category_name_conflicts(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    await _create_category(client, auth_headers)
    resp = await _create_category(client, auth_headers)
    assert resp.status_code == 409


async def test_rename_keeps_slug_stable(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    created = await _create_category(client, auth_headers)
    category_id = created.json()["id"]

    resp = await client.patch(
        f"/api/v1/admin/categories/{category_id}", json={"name": "Cakes & Pastries"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["slug"] == "cakes"
    assert resp.json()["name"] == "Cakes & Pastries"


async def test_delete_category_with_products_conflicts(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    created = await _create_category(client, auth_headers)
    category_id = created.json()["id"]

    await client.post(
        "/api/v1/admin/products",
        json={"category_id": category_id, "name": "Chocolate Cake", "base_price": "2000.00"},
        headers=auth_headers,
    )

    resp = await client.delete(f"/api/v1/admin/categories/{category_id}", headers=auth_headers)
    assert resp.status_code == 409


async def test_delete_empty_category_succeeds(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    created = await _create_category(client, auth_headers)
    category_id = created.json()["id"]

    resp = await client.delete(f"/api/v1/admin/categories/{category_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_reorder_categories(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    first = (await _create_category(client, auth_headers, name="Cakes")).json()
    second = (
        await _create_category(
            client, auth_headers, name="Pastries", icon_url="https://cdn.example.com/icons/pastries.png"
        )
    ).json()

    resp = await client.patch(
        "/api/v1/admin/categories/reorder",
        json={"items": [{"id": first["id"], "display_order": 5}, {"id": second["id"], "display_order": 1}]},
        headers=auth_headers,
    )
    assert resp.status_code == 204

    listing = await client.get("/api/v1/categories")
    slugs_in_order = [c["slug"] for c in listing.json()]
    assert slugs_in_order == ["pastries", "cakes"]


async def test_inactive_category_hidden_from_public_list(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    created = await _create_category(client, auth_headers)
    category_id = created.json()["id"]

    await client.patch(
        f"/api/v1/admin/categories/{category_id}", json={"is_active": False}, headers=auth_headers
    )

    resp = await client.get("/api/v1/categories")
    assert resp.json() == []

    detail = await client.get("/api/v1/categories/cakes")
    assert detail.status_code == 404
