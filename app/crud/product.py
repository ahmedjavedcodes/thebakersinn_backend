"""CRUD for products (and their nested variants)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.slug import generate_unique_slug

SortField = Literal["display_order", "price", "name", "created_at"]


async def _slug_exists(db: AsyncSession, slug: str, *, exclude_id: int | None = None) -> bool:
    stmt = select(Product.id).where(Product.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(Product.id != exclude_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_by_id(db: AsyncSession, product_id: int, *, with_variants: bool = False) -> Product | None:
    stmt = select(Product).where(Product.id == product_id)
    if with_variants:
        stmt = stmt.options(selectinload(Product.variants))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_slug(
    db: AsyncSession, slug: str, *, active_only: bool = False, with_variants: bool = False
) -> Product | None:
    stmt = select(Product).where(Product.slug == slug)
    if active_only:
        stmt = stmt.where(Product.is_available.is_(True))
    if with_variants:
        stmt = stmt.options(selectinload(Product.variants))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _apply_filters(
    stmt: Select[Any],
    *,
    category_slug: str | None,
    search: str | None,
    is_featured: bool | None,
    min_price: Decimal | None,
    max_price: Decimal | None,
    active_only: bool,
) -> Select[Any]:
    if active_only:
        stmt = stmt.where(Product.is_available.is_(True))
    if category_slug is not None:
        stmt = stmt.join(Category, Product.category_id == Category.id).where(Category.slug == category_slug)
    if search is not None:
        pattern = f"%{search}%"
        stmt = stmt.where(Product.name.ilike(pattern))
    if is_featured is not None:
        stmt = stmt.where(Product.is_featured.is_(is_featured))
    if min_price is not None:
        stmt = stmt.where(Product.base_price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Product.base_price <= max_price)
    return stmt


_SORT_COLUMNS = {
    "display_order": Product.display_order,
    "price": Product.base_price,
    "name": Product.name,
    "created_at": Product.created_at,
}


async def list_paginated(
    db: AsyncSession,
    *,
    page: int,
    size: int,
    category_slug: str | None = None,
    search: str | None = None,
    is_featured: bool | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    sort: SortField = "display_order",
    active_only: bool = True,
) -> tuple[list[Product], int]:
    base_stmt = _apply_filters(
        select(Product),
        category_slug=category_slug,
        search=search,
        is_featured=is_featured,
        min_price=min_price,
        max_price=max_price,
        active_only=active_only,
    )

    count_stmt = _apply_filters(
        select(func.count(Product.id)),
        category_slug=category_slug,
        search=search,
        is_featured=is_featured,
        min_price=min_price,
        max_price=max_price,
        active_only=active_only,
    )
    total = (await db.execute(count_stmt)).scalar_one()

    sort_column = _SORT_COLUMNS[sort]
    items_stmt = base_stmt.order_by(sort_column, Product.id).offset((page - 1) * size).limit(size)
    result = await db.execute(items_stmt)
    items = list(result.scalars().all())

    return items, total


async def create(db: AsyncSession, data: ProductCreate) -> Product:
    slug = await generate_unique_slug(data.name, exists=lambda s: _slug_exists(db, s))
    product = Product(
        category_id=data.category_id,
        name=data.name,
        slug=slug,
        description=data.description,
        base_price=data.base_price,
        currency=data.currency,
        images=[img.model_dump() for img in data.images],
        is_available=data.is_available,
        is_featured=data.is_featured,
        is_custom_order=data.is_custom_order,
        display_order=data.display_order,
        variants=[
            ProductVariant(
                label=v.label,
                price=v.price,
                display_order=v.display_order,
                is_available=v.is_available,
            )
            for v in data.variants
        ],
    )
    db.add(product)
    await db.commit()
    await db.refresh(product, attribute_names=["variants"])
    return product


async def update(db: AsyncSession, product: Product, data: ProductUpdate) -> Product:
    changes = data.model_dump(exclude_unset=True, exclude={"images", "variants"})

    if "name" in changes and changes["name"] != product.name:
        product.name = changes["name"]
        # Slug stays stable on rename per CLAUDE.md §7.

    for field in (
        "category_id",
        "description",
        "base_price",
        "currency",
        "is_available",
        "is_featured",
        "is_custom_order",
        "display_order",
    ):
        if field in changes:
            setattr(product, field, changes[field])

    if data.images is not None:
        product.images = [img.model_dump() for img in data.images]

    if data.variants is not None:
        product.variants.clear()
        for v in data.variants:
            product.variants.append(
                ProductVariant(
                    label=v.label,
                    price=v.price,
                    display_order=v.display_order,
                    is_available=v.is_available,
                )
            )

    await db.commit()
    # Full refresh: `updated_at` is expired by its onupdate= after the UPDATE and
    # would otherwise trigger lazy IO during response serialisation. Then reload
    # the variants collection too.
    await db.refresh(product)
    await db.refresh(product, attribute_names=["variants"])
    return product


async def set_availability(db: AsyncSession, product: Product, is_available: bool) -> Product:
    product.is_available = is_available
    await db.commit()
    await db.refresh(product)
    return product


async def delete(db: AsyncSession, product: Product) -> None:
    await db.delete(product)
    await db.commit()
