"""Product schemas.

One class per operation per CLAUDE.md §7. Images are a jsonb array on the
product; ProductImage enforces exactly one is_cover: true here in the
Pydantic layer, since the DB can't express that cheaply (§5).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.product_variant import ProductVariantCreate, ProductVariantRead


class ProductImage(BaseModel):
    url: str = Field(
        ..., description="Image URL.", examples=["https://cdn.thebakersinn.com/products/choc-1.jpg"]
    )
    alt: str | None = Field(
        default=None, description="Alt text for accessibility.", examples=["Chocolate Fudge Cake, side view"]
    )
    is_cover: bool = Field(
        default=False, description="True for the single cover image shown in listings.", examples=[True]
    )
    sort: int = Field(default=0, description="Display order among this product's images.", examples=[0])


def _validate_images(images: list[ProductImage]) -> list[ProductImage]:
    if not images:
        return images
    cover_count = sum(1 for img in images if img.is_cover)
    if cover_count != 1:
        raise ValueError(f"images must contain exactly one is_cover: true entry, got {cover_count}")
    return images


class ProductBase(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=200, description="Product name.", examples=["Chocolate Fudge Cake"]
    )
    description: str | None = Field(
        default=None,
        description="Longer description shown on the product detail page.",
        examples=["Rich chocolate sponge layered with fudge frosting."],
    )
    base_price: Decimal | None = Field(
        default=None,
        gt=0,
        decimal_places=2,
        description=(
            "Price in the product's currency. Required unless is_custom_order is true. "
            "If the product has variants, this is the 'from' price."
        ),
        examples=["2450.00"],
    )
    currency: str = Field(
        default="PKR", min_length=3, max_length=3, description="ISO 4217 currency code.", examples=["PKR"]
    )
    images: list[ProductImage] = Field(
        default_factory=list,
        description="Ordered image list. Exactly one entry must have is_cover: true (unless empty).",
    )
    is_available: bool = Field(default=True, description="In stock / orderable.", examples=[True])
    is_featured: bool = Field(default=False, description="Highlighted on the storefront.", examples=[False])
    is_custom_order: bool = Field(
        default=False,
        description="True for design-to-order cakes with no fixed price.",
        examples=[False],
    )
    display_order: int = Field(default=0, description="Sort order within its category.", examples=[0])


class ProductCreate(ProductBase):
    category_id: int = Field(..., description="Category this product belongs to.", examples=[1])
    variants: list[ProductVariantCreate] = Field(
        default_factory=list,
        description="Optional initial size variants. Leave empty to price by base_price alone.",
    )

    @model_validator(mode="after")
    def _check(self) -> ProductCreate:
        _validate_images(self.images)
        if not self.is_custom_order and self.base_price is None:
            raise ValueError("base_price is required unless is_custom_order is true")
        return self


class ProductUpdate(BaseModel):
    """All fields optional for PATCH. images/variants are whole-array replacements."""

    category_id: int | None = Field(default=None, description="Move to a different category.", examples=[2])
    name: str | None = Field(
        default=None, min_length=1, max_length=200, description="New name.", examples=["Chocolate Fudge Cake"]
    )
    description: str | None = Field(
        default=None, description="New description.", examples=["Updated description."]
    )
    base_price: Decimal | None = Field(
        default=None, gt=0, decimal_places=2, description="New base price.", examples=["2550.00"]
    )
    currency: str | None = Field(
        default=None, min_length=3, max_length=3, description="New currency code.", examples=["PKR"]
    )
    images: list[ProductImage] | None = Field(
        default=None, description="Replace the full images array. Exactly one is_cover: true required."
    )
    is_available: bool | None = Field(default=None, description="In stock / orderable.", examples=[True])
    is_featured: bool | None = Field(
        default=None, description="Highlighted on the storefront.", examples=[False]
    )
    is_custom_order: bool | None = Field(default=None, description="Design-to-order flag.", examples=[False])
    display_order: int | None = Field(default=None, description="New sort position.", examples=[1])
    variants: list[ProductVariantCreate] | None = Field(
        default=None, description="Replace the full variants array."
    )

    @model_validator(mode="after")
    def _check(self) -> ProductUpdate:
        if self.images is not None:
            _validate_images(self.images)
        return self


class ProductRead(BaseModel):
    """Used in list responses and nested under CategoryWithProducts."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Product ID.", examples=[42])
    category_id: int = Field(..., description="Owning category ID.", examples=[1])
    name: str = Field(..., description="Product name.", examples=["Chocolate Fudge Cake"])
    slug: str = Field(
        ..., description="URL-safe slug, unique across all products.", examples=["chocolate-fudge-cake"]
    )
    description: str | None = Field(default=None, description="Product description.")
    base_price: Decimal | None = Field(
        default=None,
        description="Price, or the 'from' price if this product has variants.",
        examples=["2450.00"],
    )
    currency: str = Field(..., description="ISO 4217 currency code.", examples=["PKR"])
    images: list[ProductImage] = Field(..., description="Ordered image list.")
    is_available: bool = Field(..., description="In stock / orderable.", examples=[True])
    is_featured: bool = Field(..., description="Highlighted on the storefront.", examples=[False])
    is_custom_order: bool = Field(..., description="Design-to-order flag.", examples=[False])
    display_order: int = Field(..., description="Sort order within its category.", examples=[0])
    created_at: datetime = Field(..., description="Creation timestamp (UTC).")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC).")


class ProductDetail(ProductRead):
    """GET /products/{slug} — adds variants."""

    variants: list[ProductVariantRead] = Field(
        default_factory=list, description="Size variants. Empty means base_price is the only price."
    )


class PaginatedProducts(BaseModel):
    items: list[ProductRead] = Field(..., description="Products on this page.")
    total: int = Field(..., description="Total matching products across all pages.", examples=[57])
    page: int = Field(..., description="Current page number, 1-indexed.", examples=[1])
    size: int = Field(..., description="Page size.", examples=[20])
    pages: int = Field(..., description="Total number of pages.", examples=[3])


class AvailabilityUpdate(BaseModel):
    is_available: bool = Field(..., description="New availability state.", examples=[False])
