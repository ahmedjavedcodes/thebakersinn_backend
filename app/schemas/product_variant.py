"""ProductVariant schemas — nested under product create/update/read.

There is no standalone /admin/product-variants endpoint (see CLAUDE.md §6);
variants are managed as part of the parent product's payload.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductVariantCreate(BaseModel):
    label: str = Field(
        ...,
        max_length=50,
        description="Free-text size label, e.g. a weight, so non-weight sizing needs no schema change.",
        examples=["2 lb"],
    )
    price: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        description="Price for this size, in the product's currency.",
        examples=["3450.00"],
    )
    display_order: int = Field(
        default=0, description="Sort order among this product's variants.", examples=[0]
    )
    is_available: bool = Field(
        default=True, description="Whether this size is currently orderable.", examples=[True]
    )


class ProductVariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Variant ID.", examples=[10])
    label: str = Field(..., description="Free-text size label.", examples=["2 lb"])
    price: Decimal = Field(..., description="Price for this size.", examples=["3450.00"])
    display_order: int = Field(..., description="Sort order among variants.", examples=[0])
    is_available: bool = Field(..., description="Whether this size is currently orderable.", examples=[True])
