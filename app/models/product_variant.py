"""ProductVariant model — same product sold at multiple sizes/weights.

label is free text ("1 lb", "2 lb", "3 lb") rather than a numeric weight so it
also covers non-weight sizing without a schema change (CLAUDE.md §5). A
variant has no meaning without its product, hence ON DELETE CASCADE.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.product import Product


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    product: Mapped[Product] = relationship("Product", back_populates="variants")

    def __repr__(self) -> str:  # pragma: no cover
        return f"ProductVariant(id={self.id!r}, label={self.label!r})"
