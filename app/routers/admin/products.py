"""Admin product endpoints — require a valid admin bearer token."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import category as category_crud
from app.crud import product as product_crud
from app.db.session import get_db
from app.schemas.product import (
    AvailabilityUpdate,
    ProductCreate,
    ProductDetail,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["admin:products"])


@router.post(
    "",
    response_model=ProductDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product under a category",
)
async def create_product(payload: ProductCreate, db: AsyncSession = Depends(get_db)) -> ProductDetail:
    category = await category_crud.get_by_id(db, payload.category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    product = await product_crud.create(db, payload)
    return ProductDetail.model_validate(product)


@router.patch(
    "/{product_id}/availability",
    response_model=ProductDetail,
    summary="Fast in/out-of-stock toggle",
)
async def update_product_availability(
    product_id: int, payload: AvailabilityUpdate, db: AsyncSession = Depends(get_db)
) -> ProductDetail:
    product = await product_crud.get_by_id(db, product_id, with_variants=True)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    product = await product_crud.set_availability(db, product, payload.is_available)
    return ProductDetail.model_validate(product)


@router.patch("/{product_id}", response_model=ProductDetail, summary="Partially update a product")
async def update_product(
    product_id: int, payload: ProductUpdate, db: AsyncSession = Depends(get_db)
) -> ProductDetail:
    product = await product_crud.get_by_id(db, product_id, with_variants=True)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if payload.category_id is not None:
        category = await category_crud.get_by_id(db, payload.category_id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    product = await product_crud.update(db, product, payload)
    return ProductDetail.model_validate(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Hard delete a product")
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)) -> None:
    product = await product_crud.get_by_id(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    await product_crud.delete(db, product)
