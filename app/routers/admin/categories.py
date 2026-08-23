"""Admin category endpoints — require a valid admin bearer token."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import category as category_crud
from app.db.session import get_db
from app.schemas.category import (
    CategoryCreate,
    CategoryRead,
    CategoryReorderRequest,
    CategoryUpdate,
)

router = APIRouter(prefix="/categories", tags=["admin:categories"])


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category (icon_url required)",
)
async def create_category(payload: CategoryCreate, db: AsyncSession = Depends(get_db)) -> CategoryRead:
    if await category_crud.get_by_name(db, payload.name) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category name already exists")
    try:
        category = await category_crud.create(db, payload)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Category name already exists"
        ) from exc
    return CategoryRead.model_validate(category)


@router.patch("/reorder", status_code=status.HTTP_204_NO_CONTENT, summary="Bulk reorder categories")
async def reorder_categories(payload: CategoryReorderRequest, db: AsyncSession = Depends(get_db)) -> None:
    await category_crud.reorder(db, [(item.id, item.display_order) for item in payload.items])


@router.patch("/{category_id}", response_model=CategoryRead, summary="Partially update a category")
async def update_category(
    category_id: int, payload: CategoryUpdate, db: AsyncSession = Depends(get_db)
) -> CategoryRead:
    category = await category_crud.get_by_id(db, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if (
        payload.name is not None
        and payload.name != category.name
        and await category_crud.get_by_name(db, payload.name) is not None
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category name already exists")

    try:
        category = await category_crud.update(db, category, payload)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Category name already exists"
        ) from exc
    return CategoryRead.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a category")
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)) -> None:
    category = await category_crud.get_by_id(db, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    product_count = await category_crud.count_products(db, category_id)
    if product_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This category has {product_count} product(s); move or delete them first.",
        )

    await category_crud.delete(db, category)
