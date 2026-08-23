"""CRUD for categories. All queries live here — routers never touch the ORM
session directly (CLAUDE.md §7).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.product import Product
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services.slug import generate_unique_slug


async def _slug_exists(db: AsyncSession, slug: str, *, exclude_id: int | None = None) -> bool:
    stmt = select(Category.id).where(Category.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(Category.id != exclude_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_by_id(db: AsyncSession, category_id: int) -> Category | None:
    return await db.get(Category, category_id)


async def get_by_slug(db: AsyncSession, slug: str, *, active_only: bool = False) -> Category | None:
    stmt = select(Category).where(Category.slug == slug)
    if active_only:
        stmt = stmt.where(Category.is_active.is_(True))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_name(db: AsyncSession, name: str) -> Category | None:
    result = await db.execute(select(Category).where(Category.name == name))
    return result.scalar_one_or_none()


async def list_all(db: AsyncSession, *, active_only: bool = False) -> list[Category]:
    stmt = select(Category).order_by(Category.display_order, Category.id)
    if active_only:
        stmt = stmt.where(Category.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_with_products(db: AsyncSession) -> list[Category]:
    """Active categories with their available products eager-loaded.
    Powers GET /categories/with-products — the primary storefront call.
    """
    stmt = (
        select(Category)
        .where(Category.is_active.is_(True))
        .options(selectinload(Category.products.and_(Product.is_available.is_(True))))
        .order_by(Category.display_order, Category.id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_products(db: AsyncSession, category_id: int) -> int:
    result = await db.execute(select(Product.id).where(Product.category_id == category_id))
    return len(result.scalars().all())


async def create(db: AsyncSession, data: CategoryCreate) -> Category:
    slug = await generate_unique_slug(data.name, exists=lambda s: _slug_exists(db, s))
    category = Category(
        name=data.name,
        slug=slug,
        description=data.description,
        icon_url=data.icon_url,
        display_order=data.display_order,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def update(db: AsyncSession, category: Category, data: CategoryUpdate) -> Category:
    changes = data.model_dump(exclude_unset=True)

    if "name" in changes and changes["name"] != category.name:
        category.name = changes["name"]
        # Slug is kept stable on rename per CLAUDE.md §7 — not regenerated here.

    for field in ("description", "icon_url", "display_order", "is_active"):
        if field in changes:
            setattr(category, field, changes[field])

    await db.commit()
    await db.refresh(category)
    return category


async def reorder(db: AsyncSession, items: list[tuple[int, int]]) -> None:
    for category_id, display_order in items:
        category = await db.get(Category, category_id)
        if category is not None:
            category.display_order = display_order
    await db.commit()


async def delete(db: AsyncSession, category: Category) -> None:
    await db.delete(category)
    await db.commit()
