"""Product model.

Notable design points from CLAUDE.md §5:
  - slug is unique globally (not per-category), so /products/{slug} needs no
    category context.
  - base_price is NUMERIC(10,2) and nullable ONLY when is_custom_order is
    true (enforced with a CHECK constraint, not just app-level validation).
  - images is a jsonb array of {"url", "alt", "is_cover", "sort"} objects.
    Exactly-one-cover is enforced in the Pydantic schema, not the DB.
  - category_id uses ON DELETE RESTRICT: deleting a category with products
    attached must fail loudly, never cascade or null out.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.product_variant import ProductVariant


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "is_custom_order = true OR base_price IS NOT NULL",
            name="ck_products_base_price_required_unless_custom",
        ),
        Index("ix_products_category_id", "category_id"),
        Index(
            "ix_products_available_featured",
            "is_available",
            "is_featured",
            postgresql_where="is_available = true",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PKR")
    images: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_custom_order: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    category: Mapped[Category] = relationship("Category", back_populates="products")
    variants: Mapped[list[ProductVariant]] = relationship(
        "ProductVariant",
        back_populates="product",
        order_by="ProductVariant.display_order",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"Product(id={self.id!r}, slug={self.slug!r})"
