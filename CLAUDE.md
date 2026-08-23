# CLAUDE.md — The Bakers Inn Backend

## 1. Project overview

REST API for **The Bakers Inn**, a bakery in Faisalabad, Pakistan (Instagram `@thebakers_inn`, est. 1987, two branches). Two consumers: an **admin panel** where the owner and employees manage the menu (create a category with an icon first, then add products with images into it), and a **public storefront** built by a separate frontend developer who consumes read-only endpoints and renders products grouped by category. The frontend dev works only from `/docs` and `/openapi.json` — he never touches the database, so response models must be fully typed with populated examples.

## 2. Domain research

Instagram was **not fetchable** (`instagram.com/thebakers_inn` is disallowed by robots.txt). Findings below come from reseller/gift-delivery catalogues that carry their menu, plus local business directories. Sources listed at the bottom of this section.

**Verified:**

- Bakery in D-Ground, Faisalabad; second branch at Heaven Habitat. Trading since **1987**; described as "the best cake in town" and known for cakes above all else.
- **Cakes are the dominant product line.** Observed catalogue (~30+ distinct cakes): Pineapple, Black Forest, White Forest, Chocolate, Rich Chocolate, Chocolate Fudge, Chocolate Chip, Chocolate Cream, Choco Mousse, Chocolate Fudge Brownie, Mix Fruit, Mix Fruit Dry, Dry Fruit Cocktail, Fruit Cocktail, Caramel, Walnut Coffee.
- **Branded/confectionery tie-in cakes are a major sub-line**: Ferrero Rocher, Lotus, Lotus Crunch, Lotus Caramel Crunch, Toblerone, Toblerone Chocolate, Kinder Bueno, Kinder KitKat, KitKat, Dairy Milk, Cadbury Drops, Bounty.
- **Products are tiered by name**: the same flavour appears as "Regular", "Special", and premium variants at different prices (e.g. Black Forest Regular vs Black Forest Special; Chocolate Chip vs Chocolate Chip Special).
- **Cakes are sold by weight and several are listed with multiple sizes at different prices** — one reseller standardises everything to 2 lbs, another lists ranges like ₨2,450–3,450 for a single cake marked "multiple sizes". Pound-based sizing (1/2/3 lb) is the norm for cakes in this market.
- **Prices are in PKR**, observed range roughly ₨2,450 – ₨4,950 for cakes. Reseller USD prices are their own markup, not the bakery's.
- **Custom/designed cakes are a stated specialty** — birthdays, anniversaries, newborns, "any design you have in mind". One directory lists their pricing as "custom pricing".

**Inferred (not confirmed — verify against the actual Instagram grid before relying on any of these):**

- `(inferred)` A "full range of bakery items" is mentioned but never itemised. Categories beyond cakes — pastries, brownies, cookies, breads, savouries/patties, beverages, festive/seasonal boxes — are **plausible but unverified**. Do not seed the database with them.
- `(inferred)` Custom cakes likely need a lead time (24–72 h) and possibly an advance/deposit. No source states this.
- `(inferred)` Eggless options, allergen labelling, and per-branch stock differences. No evidence either way.

**Modelling consequences of the above:**

1. Size/weight-based pricing is real, not hypothetical — see the variants decision in §5 and Open Decision D1.
2. "Regular / Special / premium" tiers are currently expressed as separate product names, not as a field. Keep them as separate products; do not build a tier enum.
3. The category set must be **entered by the owner**, not hardcoded from this research. Cakes is the only category we can assert with confidence.

Sources: [giftoo.com.pk catalogue](https://giftoo.com.pk/product-category/cakes/faisalabad-cakes/the-bakers-inn/) · [smilee.pk catalogue](https://smilee.pk/product-category/faisalabad-cakes/the-bakers-inn/) · [shoparcade.com catalogue](https://shoparcade.com/cakes/faisalabad-cake-delivery/bakers-inn/) · [findglocal listing](https://www.findglocal.com/PK/Faisalabad/407838279280379/The-Bakers-Inn) · [cityfacto bakery roundup](https://cityfacto.com/food/best-bakery-in-faisalabad/)

## 3. Tech stack

| Concern | Choice |
|---|---|
| Framework | FastAPI, async endpoints throughout |
| Database | PostgreSQL 16+ |
| ORM | SQLAlchemy 2.0 — typed `Mapped[]` / `mapped_column()` declarative style, async engine over `asyncpg` |
| Validation | Pydantic v2 — one schema class per operation, `model_config = ConfigDict(from_attributes=True)` |
| Migrations | Alembic (async template) |
| Lint + format | **Ruff** |
| Types | mypy (strict on `app/`) |
| Tests | pytest + pytest-asyncio + httpx `AsyncClient` |

> **ESLint → Ruff.** The original spec listed ESLint. ESLint is a JavaScript linter and does nothing for a Python codebase — Ruff replaces it for both linting and formatting. ESLint becomes relevant only if a JS/TS admin panel is added later, and would then be configured in that frontend repo, not here.

## 4. Project structure

```
app/
  main.py           FastAPI app, router registration, CORS, lifespan
  core/             config (pydantic-settings), security, dependencies
  db/               engine, session factory, Base, get_db dependency
  models/           SQLAlchemy models — category.py, product.py, user.py
  schemas/          Pydantic schemas, one module per resource
  crud/             DB access functions; all queries live here
  routers/          HTTP layer only — public/ and admin/ subpackages
  services/         image upload, slug generation, anything non-CRUD
alembic/            migration environment and versions
tests/              conftest.py + one test module per router
static/uploads/     locally-stored images (see Open Decision D2)
```

Routers contain no business logic and no queries — they validate, call `crud`/`services`, and return schemas.

## 5. Data model

Three tables. `product_variants` is **optional for v1** — see Open Decision D1.

```mermaid
erDiagram
    CATEGORIES ||--o{ PRODUCTS : contains
    PRODUCTS ||--o{ PRODUCT_VARIANTS : "priced by size"
    CATEGORIES {
        int id PK
        string name UK
        string slug UK
        text description
        string icon_url
        int display_order
        bool is_active
        timestamptz created_at
        timestamptz updated_at
    }
    PRODUCTS {
        int id PK
        int category_id FK
        string name
        string slug UK
        text description
        numeric base_price
        string currency
        jsonb images
        bool is_available
        bool is_featured
        bool is_custom_order
        int display_order
        timestamptz created_at
        timestamptz updated_at
    }
    PRODUCT_VARIANTS {
        int id PK
        int product_id FK
        string label
        numeric price
        int display_order
        bool is_available
    }
```

**categories** — `name` and `slug` both unique; `slug` generated from `name`. `icon_url` is nullable at the DB level but **required by the admin create endpoint**, because the owner's workflow is icon-first: a category exists and is visually complete before any product goes into it. `display_order` drives the storefront's category strip. Index: `slug`, and a partial index on `is_active`.

**products** — `slug` unique globally (not per category), so `/products/{slug}` needs no category context. `base_price` is `NUMERIC(10,2)`, never float. `currency` is `CHAR(3)` defaulting to `'PKR'` — a single-currency bakery, but the column costs nothing and avoids a painful migration if the reseller/export use case ever appears. `is_custom_order` marks the design-to-order cakes the research confirmed are a specialty; those may have no meaningful fixed price, so `base_price` is nullable **only** when `is_custom_order` is true (enforce with a `CHECK` constraint). Indexes: `category_id`, `slug`, partial index on `(is_available, is_featured)`.

**Product images — recommendation: `jsonb` array of image objects on `products`.** Considered three options:

- *Single `image_url` column* — rejected. Cake listings routinely show several angles, and the research shows the storefront is image-led.
- *Separate `product_images` table* — the textbook answer, and correct if images ever need their own metadata (alt text per locale, credits, per-image visibility) or independent querying. Rejected for now: it adds a join to every product read for a bakery menu that will hold tens, not thousands, of products.
- *`jsonb` array* — **chosen.** Shape: `[{"url": "...", "alt": "...", "is_cover": true, "sort": 0}]`. Ordering and cover selection are carried inside the document, the admin panel PATCHes the whole array to reorder, and the frontend gets images inline with the product with no extra query. Enforce exactly one `is_cover: true` in the Pydantic validator, not in the DB.

If image metadata requirements grow, migrating `jsonb` → `product_images` is mechanical. Revisit then.

**product_variants** — exists because the research found the same cake sold at multiple weights with different prices. `label` is free text (`"1 lb"`, `"2 lb"`, `"3 lb"`) rather than a numeric weight, so it also covers non-weight sizing without a schema change. When a product has zero variants the frontend uses `base_price` and shows no size picker; when it has variants, `base_price` is the "from" price. This keeps the public contract stable whether or not D1 lands in v1.

**FK delete behaviour — `ON DELETE RESTRICT` on `products.category_id`.** Cascade is wrong here: an employee deleting a category would silently destroy every product and its uploaded images with no undo. `SET NULL` is worse — it produces orphan products that appear nowhere on the storefront and are hard to find in the admin panel. RESTRICT forces the admin panel to say "this category has 14 products; move or delete them first", which is the correct interaction. `product_variants.product_id` uses `ON DELETE CASCADE` — a variant has no meaning without its product.

Soft-delete via `is_active` is the normal path for both categories and products; hard delete is an escape hatch. Prefer deactivating.

## 6. API endpoints

Public routes are unauthenticated and return only `is_active` / `is_available` records.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/v1/categories` | — | Categories, ordered by `display_order` |
| GET | `/api/v1/categories/{slug}` | — | One category |
| GET | `/api/v1/categories/with-products` | — | **Primary storefront call** — all categories with nested products |
| GET | `/api/v1/products` | — | Paginated; filters `category_slug`, `search`, `is_featured`, `min_price`, `max_price`; `sort` = `display_order`\|`price`\|`name`\|`created_at` |
| GET | `/api/v1/products/{slug}` | — | One product with variants and images |
| POST | `/api/v1/auth/login` | — | Returns access + refresh tokens |
| POST | `/api/v1/admin/categories` | admin | Create — `icon_url` required |
| PATCH | `/api/v1/admin/categories/{id}` | admin | Partial update |
| DELETE | `/api/v1/admin/categories/{id}` | owner | 409 if products still attached |
| PATCH | `/api/v1/admin/categories/reorder` | admin | Bulk `[{id, display_order}]` |
| POST | `/api/v1/admin/products` | admin | Create under a category |
| PATCH | `/api/v1/admin/products/{id}` | admin | Partial update, incl. images array |
| PATCH | `/api/v1/admin/products/{id}/availability` | admin | Fast in/out-of-stock toggle |
| DELETE | `/api/v1/admin/products/{id}` | owner | Hard delete |
| POST | `/api/v1/admin/uploads/image` | admin | `multipart/form-data`, returns `{url}` |

**Conventions.** No response envelope — return the resource or a list directly; FastAPI's OpenAPI output is cleaner without a wrapper, and the frontend dev reads types straight from it. List endpoints return `{items, total, page, size, pages}`. Errors are `{"detail": "..."}` for simple cases and FastAPI's default 422 shape for validation. Status codes: 200, 201 create, 204 delete, 401 unauthenticated, 403 wrong role, 404, 409 conflict (duplicate slug, category not empty), 422 validation.

**Auth (assumed default — confirm, Open Decision D3):** JWT bearer, `owner` and `employee` roles. Employees do everything except delete. No public signup — the owner account is seeded, employees are created by the owner.

## 7. Conventions

- `snake_case` everywhere in DB and Python, and in JSON too. No camelCase conversion layer — tell the frontend dev once.
- Slugs are auto-generated from `name` on create, kept stable on rename unless explicitly overridden, and uniqueness-checked with a numeric suffix.
- Async all the way: `async def` endpoints, `AsyncSession` injected via `Depends(get_db)`. Never open a session inside `crud`.
- Never reuse a Pydantic schema across operations. `CategoryCreate` / `CategoryUpdate` (all fields optional) / `CategoryRead` / `CategoryWithProducts`; same shape for products.
- Money is `Decimal` in Python and `NUMERIC` in Postgres. Never float.
- Every schema field gets a `description` and `examples` — that output *is* the frontend dev's documentation.
- Every model change ships with an Alembic migration in the same commit.
- Timestamps are `timestamptz`, stored UTC.

## 8. Commands

⚠️ **Unverified** — nothing is installed yet. Confirm these once the project is scaffolded.

```bash
uvicorn app.main:app --reload           # dev server → http://localhost:8000/docs
alembic revision --autogenerate -m ""   # create migration
alembic upgrade head                    # apply migrations
ruff format . && ruff check . --fix     # format + lint
mypy app                                # typecheck
pytest -q                               # tests
docker compose up -d db                 # local Postgres
```

## 9. Environment variables

```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/bakers_inn
SECRET_KEY=
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
IMAGE_STORAGE=local                  # local | s3 | cloudinary
UPLOAD_DIR=./static/uploads
MAX_UPLOAD_MB=5
ENVIRONMENT=development
```

## 10. Open decisions

- **D1 — Size variants in v1?** Research shows the same cake priced at multiple weights. Ship `product_variants` now, or ship `base_price` only and add variants later? Shipping later means a breaking change to the product response the frontend has already built against. *(Recommendation: include the table now, allow zero variants.)*
- **D2 — Where do images live?** Local `static/uploads` is simplest but ties images to one server and complicates deploys. Cloudinary gives free transforms and CDN delivery, which matters for an image-heavy bakery menu on Pakistani mobile connections. Which?
- **D3 — Auth model.** Is JWT with `owner`/`employee` right, or is a single shared admin login enough for a two-branch bakery?
- **D4 — Which categories actually exist?** Only "cakes" is confirmed. Get the real category list from the owner or the Instagram highlights before seeding anything.
- **D5 — Custom cake orders.** Are these just products flagged `is_custom_order`, or do they need a lead-time field, a deposit amount, and an enquiry/order endpoint? This is the largest potential scope change.
- **D6 — Branches.** Two locations exist. Is stock/availability per-branch, or is one menu shared? Per-branch availability would add a `branches` table and a join table.
- **D7 — Category icons.** Uploaded images, or names from an icon set the frontend renders? Changes whether `icon_url` is a URL or an identifier.
- **D8 — Instagram.** Can you export or screenshot the account's highlights and grid? The research above is second-hand from resellers and may not match their current menu.
