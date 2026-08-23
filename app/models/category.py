"""Category model.

Owner workflow is icon-first: a category is created with its icon before any
product goes into it. icon_url is nullable at the DB level (a category can in
principle exist without one) but the admin create endpoint requires it — see
CLAUDE.md §5.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.product import Product


class Category(TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (Index("ix_categories_is_active", "is_active", postgresql_where="is_active = true"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    products: Mapped[list[Product]] = relationship(
        "Product",
        back_populates="category",
        order_by="Product.display_order",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"Category(id={self.id!r}, slug={self.slug!r})"
