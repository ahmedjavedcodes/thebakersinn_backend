from __future__ import annotations

from httpx import AsyncClient


async def _create_category(client: AsyncClient, headers: dict[str, str]) -> int:
    resp = await client.post(
        "/api/v1/admin/categories",
        json={
            "name": "Cakes",
            "display_order": 0,
            "icon_url": "https://cdn.example.com/icons/cakes.png",
        },
        headers=headers,
    )
    return resp.json()["id"]


async def test_create_product_requires_base_price_unless_custom(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    category_id = await _create_category(client, auth_headers)

    resp = await client.post(
        "/api/v1/admin/products",
        json={"category_id": category_id, "name": "No Price Cake"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_custom_order_product_without_price_succeeds(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    category_id = await _create_category(client, auth_headers)

    resp = await client.post(
        "/api/v1/admin/products",
        json={"category_id": category_id, "name": "Custom Birthday Cake", "is_custom_order": True},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["base_price"] is None


async def test_images_require_exactly_one_cover(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    category_id = await _create_category(client, auth_headers)

    resp = await client.post(
        "/api/v1/admin/products",
        json={
            "category_id": category_id,
            "name": "Two Covers",
            "base_price": "100.00",
            "images": [{"url": "a", "is_cover": True}, {"url": "b", "is_cover": True}],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_product_with_variants_round_trips(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    category_id = await _create_category(client, auth_headers)

    created = await client.post(
        "/api/v1/admin/products",
        json={
            "category_id": category_id,
            "name": "Black Forest Regular",
            "base_price": "2450.00",
            "variants": [
                {"label": "1 lb", "price": "1450.00", "display_order": 0},
                {"label": "2 lb", "price": "2450.00", "display_order": 1},
            ],
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    slug = created.json()["slug"]

    resp = await client.get(f"/api/v1/products/{slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["variants"]) == 2
    assert body["variants"][0]["label"] == "1 lb"


async def test_availability_toggle_hides_from_public_list(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    category_id = await _create_category(client, auth_headers)
    created = await client.post(
        "/api/v1/admin/products",
        json={"category_id": category_id, "name": "Chocolate Cake", "base_price": "2000.00"},
        headers=auth_headers,
    )
    product_id = created.json()["id"]

    resp = await client.patch(
        f"/api/v1/admin/products/{product_id}/availability",
        json={"is_available": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_available"] is False

    listing = await client.get("/api/v1/products")
    assert listing.json()["items"] == []


async def test_category_with_products_nests_available_products(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    category_id = await _create_category(client, auth_headers)
    await client.post(
        "/api/v1/admin/products",
        json={"category_id": category_id, "name": "Chocolate Cake", "base_price": "2000.00"},
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/categories/with-products")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert len(body[0]["products"]) == 1
    assert body[0]["products"][0]["name"] == "Chocolate Cake"


async def test_filter_by_category_slug_and_price_range(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    category_id = await _create_category(client, auth_headers)
    for name, price in [("Cheap Cake", "500.00"), ("Mid Cake", "1500.00"), ("Pricey Cake", "3000.00")]:
        await client.post(
            "/api/v1/admin/products",
            json={"category_id": category_id, "name": name, "base_price": price},
            headers=auth_headers,
        )

    resp = await client.get(
        "/api/v1/products", params={"category_slug": "cakes", "min_price": "1000", "max_price": "2000"}
    )
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Mid Cake"


async def test_delete_product_hard_deletes(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    category_id = await _create_category(client, auth_headers)
    created = await client.post(
        "/api/v1/admin/products",
        json={"category_id": category_id, "name": "Chocolate Cake", "base_price": "2000.00"},
        headers=auth_headers,
    )
    product_id = created.json()["id"]

    resp = await client.delete(f"/api/v1/admin/products/{product_id}", headers=auth_headers)
    assert resp.status_code == 204

    follow_up = await client.get("/api/v1/products/chocolate-cake")
    assert follow_up.status_code == 404
