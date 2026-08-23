"""Category schemas.

One class per operation per CLAUDE.md §7 — never reuse a schema across
endpoints, even where the fields overlap. Every field carries a description
and examples, since /docs is the frontend dev's only spec.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductRead


class CategoryBase(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Display name of the category.",
        examples=["Cakes"],
    )
    description: str | None = Field(
        default=None,
        description="Optional longer description shown on the storefront category page.",
        examples=["Our signature layered cakes, made fresh daily."],
    )
    display_order: int = Field(
        default=0,
        description="Sort order for the storefront category strip. Lower shows first.",
        examples=[0],
    )


class CategoryCreate(CategoryBase):
    icon_url: str = Field(
        ...,
        description=(
            "URL of the category icon. Required on create — the admin workflow is "
            "icon-first, a category should never be created without one."
        ),
        examples=["https://cdn.thebakersinn.com/icons/cakes.png"],
    )


class CategoryUpdate(BaseModel):
    """All fields optional for PATCH."""

    name: str | None = Field(
        default=None, min_length=1, max_length=120, description="New display name.", examples=["Cakes"]
    )
    description: str | None = Field(
        default=None, description="New description.", examples=["Our signature layered cakes."]
    )
    icon_url: str | None = Field(
        default=None,
        description="New icon URL.",
        examples=["https://cdn.thebakersinn.com/icons/cakes.png"],
    )
    display_order: int | None = Field(default=None, description="New sort position.", examples=[1])
    is_active: bool | None = Field(
        default=None,
        description="Set false to hide from the public storefront without deleting.",
        examples=[True],
    )


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Category ID.", examples=[1])
    slug: str = Field(..., description="URL-safe slug, generated from name.", examples=["cakes"])
    icon_url: str | None = Field(
        default=None,
        description="URL of the category icon.",
        examples=["https://cdn.thebakersinn.com/icons/cakes.png"],
    )
    is_active: bool = Field(
        ..., description="Whether this category is visible on the storefront.", examples=[True]
    )
    created_at: datetime = Field(..., description="Creation timestamp (UTC).")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC).")


class CategoryWithProducts(CategoryRead):
    """GET /categories/with-products — the primary storefront call."""

    products: list[ProductRead] = Field(
        default_factory=list, description="Available products in this category, ordered by display_order."
    )


class CategoryReorderItem(BaseModel):
    id: int = Field(..., description="Category ID to reposition.", examples=[3])
    display_order: int = Field(..., description="New sort position.", examples=[2])


class CategoryReorderRequest(BaseModel):
    items: list[CategoryReorderItem] = Field(
        ...,
        description="Bulk list of category IDs with their new display_order.",
        examples=[[{"id": 3, "display_order": 0}, {"id": 1, "display_order": 1}]],
    )
