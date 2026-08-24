# Prompts Log

AI prompts used while building the backend this week, grouped by task.

## Domain research

- "Research The Bakers Inn (Instagram @thebakers_inn, bakery in Faisalabad, Pakistan) so we can design a realistic product catalog — find product names, categories, pricing, and anything about custom cake orders. Note clearly what's verified vs. inferred."

## Project scaffolding & tech stack

- "Set up a FastAPI backend for this bakery: async SQLAlchemy 2.0 with asyncpg, Pydantic v2 schemas, Alembic migrations, Ruff for lint/format, mypy strict, pytest + pytest-asyncio + httpx AsyncClient. Lay out the project as app/{core,db,models,schemas,crud,routers,services}, with routers split into public/ and admin/."
- "The original spec says ESLint — that's a JS linter, not applicable to a Python project. Document in CLAUDE.md why Ruff replaces it."

## Data modeling (ORM + relationships)

- "Design the schema for categories, products, and product_variants. Products belong to a category; a category has many products; a product can have many size/price variants. Use SQLAlchemy 2.0 typed Mapped[] / mapped_column() style."
- "base_price should be nullable only when is_custom_order is true — enforce that with a DB CHECK constraint, not just app-level validation. Money should always be Decimal/NUMERIC(10,2), never float."
- "What should ON DELETE behavior be for products.category_id vs product_variants.product_id? Walk through cascade vs restrict vs set null and pick the safest option for an admin accidentally deleting a category with products in it."
- "Store product images as a jsonb array of {url, alt, is_cover, sort} objects on the product row instead of a separate table — justify that decision against a normalized product_images table."
- "Generate the Alembic migration for the initial schema (categories, products, product_variants) including indexes and the base_price check constraint."

## CRUD REST API

- "Build full CRUD for the products resource: admin POST/PATCH/DELETE endpoints plus a public GET list with pagination and filters (category_slug, search, is_featured, min_price, max_price, sort) and GET by slug for a single product."
- "Add category CRUD too, including a reorder endpoint (bulk PATCH of display_order) and a with-products endpoint for the storefront's primary landing call."
- "Add a fast admin-only PATCH endpoint just for toggling product availability, separate from the general update endpoint."
- "Routers should contain no business logic or queries — only validate input, call crud/services, and return schemas. Move all DB access into app/crud."

## Input validation & status codes

- "Write Pydantic v2 schemas for products and categories — separate Create/Update/Read classes per resource, never reuse one schema across operations. Every field needs a description and examples since the frontend dev only reads /docs."
- "Add a Pydantic validator on the product images array that enforces exactly one is_cover: true."
- "What HTTP status codes should each endpoint return? Walk through 201 on create, 204 on delete, 404 vs 409 for duplicate slug and non-empty category on delete, 422 for validation failures, 401/403 for auth."

## Auth

- "Add JWT bearer auth with owner and employee roles. Employees can do everything except delete; only owner can delete categories/products. No public signup — seed the owner account."
- "Write the login endpoint that issues access + refresh tokens, and the FastAPI dependency that resolves the current user and role from the bearer token."

## Linting

- "Configure Ruff in pyproject.toml — line length 110, target py313, and turn on the E, F, I, UP, B, SIM rule sets. Ignore B008 since it flags FastAPI's Depends()/Query() default-argument pattern, which is the intended usage."
- "Run ruff check . and fix every finding until it's a clean pass."

## Unit tests

- "Write pytest + httpx AsyncClient tests for the auth, categories, and products routers — cover the happy path for each CRUD operation plus the main failure cases (duplicate slug, deleting a non-empty category, validation errors, unauthenticated/forbidden access)."
- "Review these AI-generated tests: check they're actually asserting the right status codes and response shapes, not just exercising the endpoint without meaningful assertions."
- "Set up conftest.py with an async test client and a way to reset/seed the test database between tests."

## Review / cleanup

- "Review the backend against the assignment checklist (CRUD API, ORM with a relationship, validation + status codes, linter clean pass, reviewed AI-generated tests, prompts.md) and tell me what's missing."
