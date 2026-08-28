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

## Password hashing — salt + pepper (Week 3)

- "We already bcrypt passwords with a per-password salt. Add an application-wide pepper: HMAC-SHA256(PASSWORD_PEPPER, password) before bcrypt, base64-encoded so it's NUL-free and under bcrypt's 72-byte limit. Keep hash_password/verify_password signatures unchanged. Add PASSWORD_PEPPER to config as a required setting and document it in .env.example and CLAUDE.md."
- "Add unit tests: hash is bcrypt and verifies, same password hashes differently (salt), rotating the pepper breaks verification, and long passwords sharing a 72-byte prefix still get distinct hashes."

## Role-based authorization (Week 3, Task 2)

- "Reverse D3: give admin_users a `role` column ('owner' | 'employee') as a non-native Enum (VARCHAR + CHECK), server_default 'employee'. Ship the Alembic migration in the same commit. The startup seed must force the ADMIN_EMAIL account to 'owner' so the backfill can't lock everyone out."
- "Add a `require_owner` FastAPI dependency layered on get_current_admin — employees authenticate fine but get 403 on owner-only actions. Gate DELETE /admin/categories/{id} and DELETE /admin/products/{id} with it."
- "Build owner-only `/api/v1/admin/users`: GET list (id, email, role, is_active), POST create (email, password, role default employee), PATCH (activate/deactivate + change role). Block demoting/deactivating the last active owner or your own account with a 409."
- "Add an `employee_invitations` table backing both onboarding paths: owner-sent invites (status 'pending' + random token, 7-day expiry) and self-serve join requests (status 'requested', no token until an owner approves). One live invitation per email."
- "Owner-only invitation endpoints: GET /admin/invitations (incl. pending requests), POST /admin/invitations {email, role}, POST /admin/invitations/{id}/approve, DELETE /admin/invitations/{id} (revoke)."
- "Public acceptance endpoints under /auth: POST /auth/join-requests {email} (always 202, don't leak whether the email is known), GET /auth/invitations/{token} (email + role, 410 if dead), POST /auth/invitations/{token}/accept {password} → creates the account with the invited role and returns a token pair."
- "Write tests contrasting owner vs employee: employee gets 403 on deletes and on all of /admin/users and /admin/invitations; owner succeeds; full invite→accept→login flow; join-request→approve→accept flow; expired/revoked/double-accept all rejected; last-owner and self-lockout guards return 409. Add owner_headers / employee_headers fixtures to conftest."

## Linting

- "Configure Ruff in pyproject.toml — line length 110, target py313, and turn on the E, F, I, UP, B, SIM rule sets. Ignore B008 since it flags FastAPI's Depends()/Query() default-argument pattern, which is the intended usage."
- "Run ruff check . and fix every finding until it's a clean pass."

## Unit tests

- "Write pytest + httpx AsyncClient tests for the auth, categories, and products routers — cover the happy path for each CRUD operation plus the main failure cases (duplicate slug, deleting a non-empty category, validation errors, unauthenticated/forbidden access)."
- "Review these AI-generated tests: check they're actually asserting the right status codes and response shapes, not just exercising the endpoint without meaningful assertions."
- "Set up conftest.py with an async test client and a way to reset/seed the test database between tests."

## API + integration testing (Week 3, Tasks 4–5)

- "Walk every endpoint in the OpenAPI spec once against an isolated test database — happy path plus the error path for each (401 without a token, 403 wrong role, 404, 409, 410, 422). Report expected vs actual status for each call."
- "The endpoint walk 500s on PATCH /admin/products/{id}: `product_crud.update` only refreshes the `variants` relationship after commit, so `updated_at` (expired by its onupdate=) triggers lazy IO during response serialization → MissingGreenlet. Do a full `db.refresh(product)` like `category_crud.update` and `set_availability` already do, and add a regression test that PATCHes a product and asserts the full ProductDetail comes back."
- "Add an end-to-end integration test that runs the happy path in one flow: log in → create category → create product → toggle availability → fetch it from the public storefront endpoint → delete it."

## Frontend ↔ backend connection check (Week 3, Task 3)

- "Run the backend (uvicorn) and the Next.js frontend (next dev) together and verify the wiring end to end: storefront Server Components render live catalog data; the /api/auth/login route handler proxies to the backend and stores httpOnly cookies; the /api/admin/[...path] proxy forwards Bearer auth with refresh-on-401; full CRUD from the admin panel round-trips to Postgres; unauthenticated /admin/* redirects to /admin/login."

## Review / cleanup

- "Review the backend against the assignment checklist (CRUD API, ORM with a relationship, validation + status codes, linter clean pass, reviewed AI-generated tests, prompts.md) and tell me what's missing."
- "Re-run ruff, mypy, and the full pytest suite, plus an Alembic downgrade/upgrade roundtrip, after the auth changes and confirm everything is green."
