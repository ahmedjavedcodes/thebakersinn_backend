"""End-to-end happy path in a single flow (assignment Task 5).

login -> create category -> create product (with a variant) -> edit it ->
toggle availability -> read it back from the PUBLIC storefront endpoints ->
delete it -> confirm it's gone.
"""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


async def test_full_admin_to_storefront_happy_path(client: AsyncClient, admin_token: str) -> None:
    # 1. log in for real (not just the fixture token)
    login = await client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # 2. create a category
    cat = await client.post(
        "/api/v1/admin/categories",
        json={"name": "Cakes", "display_order": 0, "icon_url": "https://cdn.example.com/cakes.png"},
        headers=headers,
    )
    assert cat.status_code == 201
    category_id = cat.json()["id"]

    # 3. create a product with a size variant
    created = await client.post(
        "/api/v1/admin/products",
        json={
            "category_id": category_id,
            "name": "Black Forest",
            "base_price": "2450.00",
            "is_featured": True,
            "variants": [{"label": "1 lb", "price": "1450.00", "display_order": 0}],
        },
        headers=headers,
    )
    assert created.status_code == 201
    product_id = created.json()["id"]
    slug = created.json()["slug"]

    # 4. edit it
    edited = await client.patch(
        f"/api/v1/admin/products/{product_id}",
        json={"description": "Whipped cream, cherries, chocolate shavings."},
        headers=headers,
    )
    assert edited.status_code == 200
    assert edited.json()["description"].startswith("Whipped cream")

    # 5. make sure it's available
    toggled = await client.patch(
        f"/api/v1/admin/products/{product_id}/availability",
        json={"is_available": True},
        headers=headers,
    )
    assert toggled.status_code == 200

    # 6. it now shows up on the PUBLIC storefront
    listing = await client.get("/api/v1/products", params={"category_slug": "cakes"})
    assert listing.status_code == 200
    assert [p["name"] for p in listing.json()["items"]] == ["Black Forest"]

    detail = await client.get(f"/api/v1/products/{slug}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["base_price"] == "2450.00"
    assert [v["label"] for v in body["variants"]] == ["1 lb"]

    nested = await client.get("/api/v1/categories/with-products")
    assert nested.status_code == 200
    assert nested.json()[0]["products"][0]["name"] == "Black Forest"

    # 7. delete it, and the storefront forgets it
    assert (await client.delete(f"/api/v1/admin/products/{product_id}", headers=headers)).status_code == 204
    assert (await client.get(f"/api/v1/products/{slug}")).status_code == 404
    assert (await client.get("/api/v1/products")).json()["items"] == []

    # category is empty now, so it can be deleted too
    assert (
        await client.delete(f"/api/v1/admin/categories/{category_id}", headers=headers)
    ).status_code == 204
