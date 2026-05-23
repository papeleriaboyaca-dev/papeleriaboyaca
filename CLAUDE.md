# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Repository Overview

**Papelería Boyacá v2** — Colombian e-commerce platform for a stationery store. Full-stack: 5 FastAPI microservices + React 19 frontend.

---

## Commands

### Backend (from `papeleriav2/` root)

```bash
# Start all services (always use --env-file deploy/.env)
make start
# equivalent: docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build --no-cache

make stop
make restart
make logs

# Run unit tests per service (no Docker needed, SQLite in-memory)
make test
# Run a single service's unit tests:
cd order-service && pytest tests/test_order_service.py -v -p no:warnings

# Run HTTP tests (spin up the service without Docker):
cd catalog-service && pytest tests/test_http_catalog.py -v

# Smoke tests (requires running stack):
pytest tests_smoke/ -v

# Integration tests (spins up Postgres on port 5433):
make test-integration

# Coverage:
make test-cov

# Lint / Format:
make lint       # flake8, max-line-length=120
make format     # black + isort
```

### Frontend (`papeleriav2/frontend/`)

```bash
pnpm dev        # dev server at :5173, proxies /api → :8083
pnpm build      # tsc -b && vite build
pnpm lint       # eslint
```

---

## Architecture

### Backend — Microservices

All traffic enters through the **API Gateway** (port 8083). Internal service ports are bound to `127.0.0.1` only; only the gateway is publicly accessible.

```
Client → API Gateway (:8083)
              ├── Identity Service  (:8004)  — Supabase Auth, users, roles
              ├── Catalog Service   (:8002)  — products, categories, stock
              ├── Order Service     (:8003)  — orders, order items, history
              └── Payment Service   (:8005)  — Wompi transactions, webhooks
```

Each service connects to **Supabase PostgreSQL** using its own isolated schema (`identity_service`, `catalog_service`, `order_service`, `payment_service`). The `DATABASE_URL` must use Supabase's Session Pooler (port 6543), not the Transaction Pooler (port 5432).

### Internal Service Layout (hexagonal)

Each microservice follows the same four-layer pattern:

```
src/
  domain/          # Entities and pure business rules (no FastAPI, no SQLAlchemy)
  application/     # Use cases + Pydantic DTOs
  infrastructure/  # SQLAlchemy models, repositories, external clients
  interfaces/      # FastAPI router (http.py)
  config.py        # Settings via pydantic-settings
  main.py          # FastAPI app startup
```

### JWT / Auth Flow

1. Supabase issues **ES256** (ECDSA P-256) JWTs with a custom claim `user_role: "CLIENTE" | "ADMIN" | "SUPERADMIN"`.
2. The gateway fetches the JWKS public key from Supabase at startup and caches it (`_load_supabase_key()`). Falls back to `SUPABASE_JWT_SECRET` (HS256) if JWKS is unavailable.
3. Downstream services trust that any request that reached them was already authenticated. They never perform JWT validation themselves — they receive `user_id` (the `sub` claim) as a query parameter injected by the gateway.

### Role-Based Access (Gateway)

Three gateway dependency functions in `api-gateway/src/interfaces/http.py`:
- `get_current_user` — validates JWT, returns decoded payload
- `require_role(*roles)` — allows only specified roles (e.g. `"ADMIN"`, `"SUPERADMIN"`)
- `require_client_only` — blocks ADMIN/SUPERADMIN (used on checkout, order creation, payment, addresses)

Role is read from `user.get("user_role") or user.get("role")` and uppercased.

### Admin vs Client separation

ADMIN and SUPERADMIN are back-office users. They **cannot** create orders or initiate payments. They can see and manage all orders/transactions via `is_admin=true` query parameter passthrough. SUPERADMIN additionally manages users.

The gateway passes `is_admin=true` (without `user_id`) for admin requests to order-service and payment-service so those services return all records instead of filtering by user.

### Payment Flow (Wompi)

Two-step process:
1. `POST /pagos/transactions` → creates a `Transaction` record in DB (`status=pending`)
2. `POST /pagos/checkout` → calls Wompi API, updates transaction to `status=processing`, returns `async_payment_url` for async methods (Nequi, PSE) or confirmation for synchronous ones
3. Wompi webhook → `POST /pagos/webhooks/wompi` → updates transaction status and calls order-service to update order status

### Frontend

React 19 + Vite 8 + TypeScript. State: TanStack Query v5 (server state) + Zustand v5 (auth, cart, toasts). Forms: react-hook-form + zod.

`src/lib/axios.ts` — `api` instance with base `/api`, auto-attaches `Authorization` header from `localStorage`, redirects to `/login` on 401.

Vite dev server proxies `/api/*` → `http://localhost:8083` (configured in `vite.config.ts`).

**Stores:**
- `authStore` — JWT token + parsed payload (persisted via zustand/middleware). Use `useAuthStore((s) => s.user?.user_role)` for role checks.
- `cartStore` — cart items + total, not persisted to server.
- `toastStore` — transient notifications; use `toast.success()` / `toast.error()` singleton.

**Services** (`src/services/`) — thin wrappers around `api` (axios). One file per domain: `auth`, `catalog`, `orders`, `payments`, `admin`, `addresses`.

**Types** (`src/types/index.ts`) — all shared interfaces live here. `OrderStatus` and `PaymentMethod` are string union types matching backend lowercase values.

**Admin pages** are under `/admin` route, guarded by `RequireAuth roles={["ADMIN", "SUPERADMIN"]}`. SUPERADMIN-only sections (user management, payment stats) are conditionally rendered based on `user?.user_role === "SUPERADMIN"`.

---

## Key Conventions

- **Monetary values**: `Numeric(14, 2)` in SQLAlchemy models (not `Float`). Apply `deploy/schema_migration_numeric.sql` against Supabase when changing schemas.
- **Status values**: lowercase in DB and API (`pending`, `confirmed`, `processing`, `shipped`, `delivered`, `cancelled`). Frontend maps them to Spanish labels via `STATUS_LABEL` records.
- **Order audit trail**: `OrderHistoryRepository` writes a row to `order_service.order_history` on every status change, including order creation. Wired in `OrderService.__init__` alongside other repos.
- **Stock management**: Stock is reduced atomically at order creation (not at payment). On cancel, stock is restored. There is no deferred reservation.
- **Soft delete for products**: `DELETE /productos/{id}` sets `is_active=false`, never deletes the row.
- **Active-only filter**: `GET /productos` passes `active_only=false` for admin users so they see inactive products too.

---

## Environment

Credentials live in `deploy/.env` (gitignored). Never use `.env.local` or other locations — docker-compose.yml and Makefile are hardcoded to `--env-file deploy/.env`.

Required variables: `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_JWT_SECRET`, `WOMPI_PRIVATE_KEY`, `WOMPI_PUBLIC_KEY`, `WOMPI_EVENTS_SECRET`, `WOMPI_INTEGRITY_SECRET`.

`WOMPI_TEST_MODE=true` by default; set to `false` and use production keys for live payments.

---

## Database Migrations

Schema is managed manually via SQL files run in Supabase's SQL Editor:
- `schema.sql` — initial full schema
- `deploy/schema_migration_numeric.sql` — Float → Numeric migration for all monetary columns
