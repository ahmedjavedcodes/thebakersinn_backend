"""Public product endpoints — unauthenticated, is_available records only."""

from __future__ import annotations

import math
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import product as product_crud
from app.crud.product import SortField
from app.db.session import get_db
from app.schemas.product import PaginatedProducts, ProductDetail, ProductRead

router = APIRouter(prefix="/products", tags=["products"])


@router.get(
    "",
    response_model=PaginatedProducts,
    summary="List available products, paginated and filterable",
)
async def list_products(
    db: AsyncSession = Depends(get_db),
    category_slug: str | None = Query(
        default=None, description="Filter by category slug.", examples=["cakes"]
    ),
    search: str | None = Query(
        default=None, description="Case-insensitive name search.", examples=["chocolate"]
    ),
    is_featured: bool | None = Query(default=None, description="Filter to featured products only."),
    min_price: Decimal | None = Query(default=None, ge=0, description="Minimum base_price."),
    max_price: Decimal | None = Query(default=None, ge=0, description="Maximum base_price."),
    sort: SortField = Query(default="display_order", description="Sort field."),
    page: int = Query(default=1, ge=1, description="1-indexed page number."),
    size: int = Query(default=20, ge=1, le=100, description="Items per page."),
) -> PaginatedProducts:
    items, total = await product_crud.list_paginated(
        db,
        page=page,
        size=size,
        category_slug=category_slug,
        search=search,
        is_featured=is_featured,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        active_only=True,
    )
    pages = math.ceil(total / size) if total else 0
    return PaginatedProducts(
        items=[ProductRead.model_validate(p) for p in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get(
    "/{slug}",
    response_model=ProductDetail,
    summary="Get one available product with variants and images",
)
async def get_product(slug: str, db: AsyncSession = Depends(get_db)) -> ProductDetail:
    product = await product_crud.get_by_slug(db, slug, active_only=True, with_variants=True)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return ProductDetail.model_validate(product)
