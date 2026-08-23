"""Declarative base for all SQLAlchemy models."""

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    # Every Mapped[datetime] column becomes timestamptz by default, per
    # CLAUDE.md §7 ("Timestamps are timestamptz, stored UTC") — no need to
    # spell out DateTime(timezone=True) on each column.
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }
