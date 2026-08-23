"""Public category endpoints — unauthenticated, active records only."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import category as category_crud
from app.db.session import get_db
from app.schemas.category import CategoryRead, CategoryWithProducts

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get(
    "/with-products",
    response_model=list[CategoryWithProducts],
    summary="All active categories with their available products nested",
    description="The primary storefront call: every active category, ordered by display_order, "
    "with its available products nested inline.",
)
async def list_categories_with_products(
    db: AsyncSession = Depends(get_db),
) -> list[CategoryWithProducts]:
    categories = await category_crud.list_with_products(db)
    return [CategoryWithProducts.model_validate(c) for c in categories]


@router.get(
    "",
    response_model=list[CategoryRead],
    summary="List active categories",
    description="Active categories ordered by display_order, for the storefront category strip.",
)
async def list_categories(db: AsyncSession = Depends(get_db)) -> list[CategoryRead]:
    categories = await category_crud.list_all(db, active_only=True)
    return [CategoryRead.model_validate(c) for c in categories]


@router.get(
    "/{slug}",
    response_model=CategoryRead,
    summary="Get one active category by slug",
)
async def get_category(slug: str, db: AsyncSession = Depends(get_db)) -> CategoryRead:
    category = await category_crud.get_by_slug(db, slug, active_only=True)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return CategoryRead.model_validate(category)
