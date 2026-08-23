"""Slug generation with numeric-suffix uniqueness (CLAUDE.md §7).

Slugs are generated from name on create, kept stable on rename unless
explicitly overridden by the caller, and uniqueness-checked with a numeric
suffix (-2, -3, ...).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from slugify import slugify


async def generate_unique_slug(
    name: str,
    *,
    exists: Callable[[str], Awaitable[bool]],
) -> str:
    """`exists` returns True if the given slug is already taken."""
    base = slugify(name)
    candidate = base
    suffix = 2
    while await exists(candidate):
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate
