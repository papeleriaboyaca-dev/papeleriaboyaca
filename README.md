# Papelería Boyacá v2

E-commerce colombiano para papelería y útiles escolares. Arquitectura de microservicios con FastAPI + React 19, pagos reales vía Wompi.

---

## Arquitectura general

```mermaid
graph TB
    Browser["🌐 Navegador<br/>React 19 + Vite"]

    subgraph deploy["Deploy (Docker Compose)"]
        Caddy["🔒 Caddy<br/>TLS automático<br/>:80 / :443"]
        Frontend["📦 Frontend<br/>React SPA · nginx<br/>:3000"]
        Gateway["🚪 API Gateway<br/>FastAPI · slowapi<br/>:8083"]

        subgraph services["Microservicios (solo 127.0.0.1)"]
            Identity["👤 Identity<br/>:8004"]
            Catalog["📚 Catalog<br/>:8002"]
            Order["🛒 Order<br/>:8003"]
            Payment["💳 Payment<br/>:8005"]
        end
    end

    Supabase[("🐘 Supabase PostgreSQL<br/>Session Pooler :6543")]
    Wompi["💰 Wompi<br/>gateway de pagos CO"]

    Browser -->|HTTPS| Caddy
    Caddy --> Frontend
    Caddy -->|/api/*| Gateway
    Frontend -->|/api/*| Gateway

    Gateway --> Identity
    Gateway --> Catalog
    Gateway --> Order
    Gateway --> Payment

    Identity & Catalog & Order & Payment --> Supabase
    Payment <-->|API + Webhooks| Wompi
```

> Todos los servicios internos solo son accesibles dentro de la red Docker. El tráfico externo entra únicamente por Caddy (producción) o directamente al Gateway/Frontend en desarrollo local.

---

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | React 19, Vite 8, TypeScript, TanStack Query v5, Zustand v5, Tailwind CSS v4 |
| Backend | FastAPI, SQLAlchemy async, Pydantic v2, pydantic-settings |
| Auth | Supabase Auth — ES256 JWT (ECDSA P-256) con fallback HS256 |
| Base de datos | Supabase PostgreSQL (Session Pooler puerto 6543) |
| Pagos | Wompi (Colombia) |
| Deploy | Docker Compose + Caddy TLS automático |
| Tests | pytest + pytest-asyncio — 184 tests (unitarios e integración) |

---

## Flujo de autenticación JWT

```mermaid
sequenceDiagram
    actor U as Usuario
    participant GW as API Gateway
    participant ID as Identity Service
    participant SB as Supabase Auth

    U->>GW: POST /api/auth/login {email, password}
    GW->>ID: POST /auth/login
    ID->>SB: signInWithPassword()
    SB-->>ID: access_token (ES256) + refresh_token
    ID-->>GW: TokenResponse
    GW-->>U: {access_token, refresh_token}
    Note over U: sessionStorage (por pestaña)

    U->>GW: GET /api/pedidos<br/>Authorization: Bearer <token>
    GW->>GW: 1. Descarga JWKS de Supabase (cacheado)<br/>2. jwt.decode(aud="authenticated")<br/>3. Lee user_role del claim
    alt CLIENTE
        GW->>Order: GET /orders?user_id=<sub>
    else ADMIN / SUPERADMIN
        GW->>Order: GET /orders?is_admin=true
    end
    Order-->>GW: [OrderResponse]
    GW-->>U: [OrderResponse]
```

**Claims relevantes del JWT:**

| Claim | Valor |
|---|---|
| `sub` | UUID del usuario |
| `user_role` | `CLIENTE` \| `ADMIN` \| `SUPERADMIN` |
| `aud` | `"authenticated"` (requerido por el gateway) |
| `email` | Email del usuario |

---

## Flujo de pago (Wompi 2 pasos)

```mermaid
sequenceDiagram
    actor C as Cliente
    participant GW as API Gateway
    participant OS as Order Service
    participant PS as Payment Service
    participant W as Wompi

    C->>GW: POST /api/pedidos {items, address_id}
    GW->>OS: POST /orders
    OS->>OS: Reduce stock atómicamente
    OS-->>GW: Order {id, total, status: pending_payment}
    GW-->>C: Orden creada ✓

    C->>GW: POST /api/pagos/transactions {order_id, method}
    GW->>PS: POST /transactions
    PS-->>GW: Transaction {id, status: pending}

    C->>GW: POST /api/pagos/checkout {transaction_id, ...}
    GW->>PS: POST /wompi/checkout
    PS->>W: Crear transacción Wompi
    W-->>PS: {id, async_payment_url}
    PS-->>C: URL de pago Wompi

    Note over C,W: Cliente completa el pago en Wompi (Nequi, PSE, tarjeta...)

    W->>GW: POST /api/pagos/webhooks/wompi
    GW->>PS: Verificar firma SHA256
    PS->>OS: PUT /orders/{id}/status → paid
    OS-->>PS: Order actualizada
    PS-->>W: 200 OK
```

**Firma del webhook:**
```
signature = SHA256(concat(prop_values) + timestamp + WOMPI_EVENTS_SECRET)
```
donde `prop_values` son los campos definidos en `event.signature.properties`, concatenados en orden.

---

## Ciclo de vida de una orden

```mermaid
stateDiagram-v2
    direction LR

    [*] --> pending_payment: POST /pedidos\nstock reducido

    pending_payment --> paid: Webhook Wompi APPROVED
    pending_payment --> expired: Cleanup job\n> 30 min sin pago\nstock restaurado
    pending_payment --> cancelled: Admin cancela\nstock restaurado

    paid --> processing: Admin actualiza
    paid --> cancelled: Admin cancela\nstock restaurado

    processing --> shipped: Admin actualiza
    shipped --> delivered: Admin actualiza

    expired --> [*]
    cancelled --> [*]
    delivered --> [*]
```

> El **cleanup job** del Order Service corre cada 5 minutos (configurable). Expira órdenes `pending_payment` con más de 30 minutos sin pago y restaura el stock.

---

## Esquema de base de datos

Cada servicio tiene su propio schema aislado en el mismo cluster de Supabase.

```mermaid
erDiagram
    direction TB

    %% ══ identity_service ════════════════════════════
    ROLES {
        uuid    id          PK
        varchar name        "CLIENTE|ADMIN|SUPERADMIN"
        text    description
        bool    is_active
    }
    USERS {
        uuid    id          PK
        uuid    supabase_id "Supabase Auth UUID"
        varchar email       "UNIQUE"
        varchar first_name
        varchar last_name
        varchar document_id
        varchar phone
        varchar city
        uuid    role_id     FK
        bool    is_active
        ts      created_at
    }

    %% ══ catalog_service ═════════════════════════════
    CATEGORIES {
        uuid    id          PK
        varchar name
        varchar slug        "UNIQUE"
        text    description
        bool    is_active
    }
    PRODUCTS {
        uuid    id          PK
        uuid    category_id FK
        varchar sku         "UNIQUE"
        varchar name
        text    description
        numeric price       "Numeric(14,2)"
        numeric cost_price  "Numeric(14,2)"
        int     stock
        varchar image_url
        varchar sku_barcode
        bool    is_active
    }
    MARKETING_CONTENT {
        uuid    id            PK
        varchar title
        varchar type          "carousel|panel"
        text    image_url
        text    image_path
        int     display_order
        bool    is_active
        ts      created_at
    }

    %% ══ order_service ═══════════════════════════════
    ORDERS {
        uuid    id                  PK
        uuid    user_id
        varchar order_number        "UNIQUE"
        varchar status
        numeric subtotal            "Numeric(14,2)"
        numeric tax                 "Numeric(12,2)"
        numeric discount            "Numeric(12,2)"
        numeric tax_amount          "Numeric(14,2)"
        numeric discount_percentage "Numeric(5,2)"
        numeric discount_amount     "Numeric(14,2)"
        numeric total               "Numeric(14,2)"
        uuid    shipping_address_id FK
        varchar tracking_number
        varchar shipping_carrier
        ts      shipped_at
        ts      delivered_at
        ts      created_at
    }
    ORDER_ITEMS {
        uuid    id           PK
        uuid    order_id     FK
        uuid    product_id
        varchar product_name
        int     quantity
        numeric unit_price   "Numeric(14,2)"
        numeric subtotal     "Numeric(14,2)"
    }
    SHIPPING_ADDRESSES {
        uuid    id            PK
        uuid    user_id
        varchar address_line1
        varchar address_line2
        varchar city
        varchar postal_code
        varchar country
        bool    is_default
        bool    is_active
    }
    ORDER_HISTORY {
        uuid    id         PK
        uuid    order_id   FK
        varchar old_status
        varchar new_status
        uuid    changed_by
        text    notes
        ts      created_at
    }

    %% ══ payment_service ═════════════════════════════
    TRANSACTIONS {
        uuid    id                   PK
        uuid    order_id
        uuid    user_id
        numeric amount               "Numeric(14,2)"
        varchar status
        varchar payment_gateway      "wompi"
        varchar payment_method
        varchar wompi_reference      "UNIQUE"
        varchar wompi_transaction_id
        jsonb   gateway_response
        text    error_message
        jsonb   meta
        ts      created_at
    }
    WEBHOOKS_LOG {
        uuid    id              PK
        varchar event_type
        varchar wompi_reference
        varchar event_id        "UNIQUE"
        jsonb   payload
        bool    processed
        text    error_message
        ts      created_at
    }

    ROLES         ||--o{ USERS         : "asignado a"
    CATEGORIES    ||--o{ PRODUCTS      : "tiene"
    ORDERS        ||--|{ ORDER_ITEMS   : "contiene"
    ORDERS        ||--o{ ORDER_HISTORY : "historial"
    ORDERS        ||--o| SHIPPING_ADDRESSES : "envío a"
```

---

## Roles y control de acceso

```mermaid
graph LR
    subgraph roles["Roles"]
        C[CLIENTE]
        A[ADMIN]
        SA[SUPERADMIN]
    end

    subgraph rutas["Acceso a rutas"]
        PUB["📖 Público\n/catalogo, /producto/:id\n/marketing/public"]
        AUTH["🔐 Autenticado\nMis pedidos · Mi perfil\nDirecciones de envío"]
        CONLY["🛒 Solo CLIENTE\nCheckout · Crear pedido\nIniciar pago"]
        ADM["⚙️ ADMIN+\nGestión productos · Pedidos\nCategorías · Marketing"]
        SUA["👑 Solo SUPERADMIN\nGestión de usuarios\nEstadísticas de pagos"]
    end

    C & A & SA --> PUB
    C --> AUTH
    A & SA --> AUTH
    C --> CONLY
    A & SA --> ADM
    SA --> SUA
```

> ADMIN y SUPERADMIN **no pueden** crear órdenes ni iniciar pagos — el gateway aplica `require_client_only` en esas rutas.

---

## Estructura del proyecto

```
papeleriav2/
│
├── api-gateway/                 # Punto de entrada — auth, routing, rate limiting
│   └── src/interfaces/http.py   # 38 rutas proxy + validación JWT
│
├── identity-service/            # Auth vía Supabase, usuarios, roles
├── catalog-service/             # Productos, categorías, stock, marketing
├── order-service/               # Pedidos, ítems, direcciones, cleanup job
├── payment-service/             # Transacciones Wompi, webhooks
│
├── frontend/                    # React 19 SPA → nginx:alpine en producción
│   └── src/
│       ├── pages/               # catalog/ auth/ checkout/ orders/ profile/ admin/
│       ├── components/          # layout/ ui/ (ProductCard, HeroCarousel, PromoPanels…)
│       ├── services/            # Wrappers axios: auth, catalog, orders, payments, admin
│       ├── store/               # authStore (sessionStorage), cartStore (localStorage)
│       └── lib/                 # axios.ts, utils.ts, passwordRules.ts
│
├── deploy/
│   ├── docker-compose.yml
│   ├── Caddyfile                # TLS automático (perfil --profile caddy)
│   └── .env                    # ← credenciales (gitignored)
│
├── tests_integration/           # Tests contra PostgreSQL real (:5433)
├── tests_smoke/                 # Tests contra el stack completo levantado
├── schema.sql                   # DDL inicial (4 schemas PostgreSQL)
└── Makefile
```

Cada microservicio sigue **arquitectura hexagonal** con 4 capas:

```
src/
  domain/          # Entidades y reglas de negocio (sin FastAPI, sin SQLAlchemy)
  application/     # Casos de uso + DTOs Pydantic
  infrastructure/  # Modelos SQLAlchemy, repositorios, clientes HTTP internos
  interfaces/      # Router FastAPI (http.py)
```

---

## Instalación y despliegue

### Requisitos

- Docker + Docker Compose v2
- (Opcional para desarrollo) Node.js 20 + pnpm 10, Python 3.11

### 1. Variables de entorno

Crea `deploy/.env`:

```env
# Base de datos — usar Session Pooler de Supabase (puerto 6543, NO 5432)
DATABASE_URL=postgresql+asyncpg://postgres.<ref>:<password>@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# Supabase
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_KEY=<service_role_key>
SUPABASE_JWT_SECRET=<jwt_secret>

# Wompi (sandbox por defecto — cambiar a false + llaves reales para producción)
WOMPI_PUBLIC_KEY=pub_test_...
WOMPI_PRIVATE_KEY=prv_test_...
WOMPI_EVENTS_SECRET=<events_secret>
WOMPI_INTEGRITY_SECRET=<integrity_secret>
WOMPI_TEST_MODE=true

# Seguridad interna entre servicios
INTERNAL_API_SECRET=<hex_aleatorio_64_chars>

# URLs públicas (para webhooks y redirecciones de Wompi)
APP_URL=https://tudominio.com
FRONTEND_URL=https://tudominio.com
```

| Variable | Dónde conseguirla |
|---|---|
| `SUPABASE_*` | Supabase → Project Settings → API |
| `DATABASE_URL` | Supabase → Project Settings → Database → Session Pooler |
| `WOMPI_*` | [Dashboard Wompi](https://comercios.wompi.co) → Desarrolladores |

### 2. Email transaccional (Resend)

Configura SMTP en **Supabase → Project Settings → Authentication → SMTP Settings**:

```
Host:     smtp.resend.com
Port:     465
User:     resend
Password: re_xxxxxxxxxxxxxxxxxx   ← API key de resend.com
Sender:   Papelería Boyacá <noreply@mail.tudominio.com>
```

Correos que se envían automáticamente:
- **Confirmación de cuenta** al registrarse
- **Recuperación de contraseña** al solicitar reset
- **Notificación de cambio de contraseña**

### 3. Storage en Supabase

Crea dos buckets **públicos** en Supabase → Storage:

| Bucket | Para qué |
|---|---|
| `product-images` | Imágenes de productos |
| `marketing` | Banners del carrusel y paneles de la home |

### 4. Levantar

```bash
# Con Make (recomendado — reconstruye sin caché)
make start

# O directamente
docker compose -f deploy/docker-compose.yml --env-file deploy/.env build --no-cache
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d

# Con Caddy y dominio propio (TLS automático)
APP_DOMAIN=tudominio.com docker compose -f deploy/docker-compose.yml \
  --env-file deploy/.env --profile caddy up -d
```

### Comandos útiles

```bash
make start       # Rebuild sin caché + up
make stop        # down
make restart     # stop + start
make logs        # logs -f (todos los servicios)

# Rebuild de un solo servicio
docker compose -f deploy/docker-compose.yml --env-file deploy/.env \
  up -d --build catalog-service
```

### Puertos locales

| Servicio | Puerto |
|---|---|
| Frontend | http://localhost:3000 |
| API Gateway + Swagger | http://localhost:8083 / http://localhost:8083/docs |
| Catalog Service | http://localhost:8002 |
| Order Service | http://localhost:8003 |
| Identity Service | http://localhost:8004 |
| Payment Service | http://localhost:8005 |

---

## API — referencia de rutas

Todas las rutas van a través del gateway: `http://localhost:8083/api/...`

### Auth e identidad
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `POST` | `/api/auth/register` | — | Registro de usuario |
| `POST` | `/api/auth/login` | — | Login → access + refresh token |
| `POST` | `/api/auth/refresh` | — | Renovar access token |
| `POST` | `/api/auth/forgot-password` | — | Enviar email de recuperación |
| `POST` | `/api/auth/change-password` | ✓ | Cambiar contraseña |
| `GET` | `/api/users/me` | ✓ | Obtener perfil propio |
| `PUT` | `/api/users/me` | ✓ | Actualizar perfil |

### Catálogo
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/productos` | — | Listar productos |
| `GET` | `/api/productos/:id` | — | Detalle de producto |
| `GET` | `/api/categorias` | — | Listar categorías |
| `POST` | `/api/productos` | ADMIN | Crear producto |
| `PUT` | `/api/productos/:id` | ADMIN | Editar producto |
| `DELETE` | `/api/productos/:id` | ADMIN | Soft-delete (`is_active=false`) |
| `POST` | `/api/productos/:id/imagen` | ADMIN | Subir imagen |
| `POST` | `/api/categorias` | ADMIN | Crear categoría |
| `DELETE` | `/api/categorias/:id` | ADMIN | Eliminar categoría |

### Pedidos
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `POST` | `/api/pedidos` | CLIENTE | Crear pedido (reduce stock) |
| `GET` | `/api/pedidos` | ✓ | Mis pedidos (todos si ADMIN) |
| `GET` | `/api/pedidos/:id` | ✓ | Detalle de pedido |
| `GET` | `/api/pedidos/:id/items` | ✓ | Ítems del pedido |
| `PUT` | `/api/pedidos/:id/status` | ADMIN | Cambiar estado |
| `POST` | `/api/pedidos/:id/cancel` | ADMIN | Cancelar pedido |
| `GET` | `/api/addresses` | ✓ | Mis direcciones de envío |
| `POST` | `/api/addresses` | ✓ | Agregar dirección |
| `DELETE` | `/api/addresses/:id` | ✓ | Eliminar dirección |

### Pagos
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `POST` | `/api/pagos/transactions` | CLIENTE | Iniciar transacción |
| `POST` | `/api/pagos/checkout` | CLIENTE | Procesar en Wompi |
| `GET` | `/api/pagos/transactions` | ✓ | Mis transacciones (todas si ADMIN) |
| `GET` | `/api/pagos/transactions/:id` | ✓ | Detalle de transacción |
| `POST` | `/api/pagos/webhooks/wompi` | — | Webhook firmado de Wompi |

### Marketing
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/marketing/public` | — | `{carousel: [], panels: []}` para la home |
| `GET` | `/api/marketing` | ADMIN | Listar todo el contenido |
| `POST` | `/api/marketing` | ADMIN | Crear banner o panel |
| `PUT` | `/api/marketing/:id` | ADMIN | Editar |
| `DELETE` | `/api/marketing/:id` | ADMIN | Eliminar |
| `POST` | `/api/marketing/:id/imagen` | ADMIN | Subir imagen |

### Administración de usuarios
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/admin/usuarios` | SUPERADMIN | Listar todos los usuarios |
| `PUT` | `/api/admin/usuarios/:id/rol` | SUPERADMIN | Cambiar rol |
| `PUT` | `/api/admin/usuarios/:id/activo` | SUPERADMIN | Activar / desactivar |

---

## Tests

```bash
# Unitarios (sin Docker, SQLite en memoria) — 184 tests
make test

# Por servicio
cd identity-service && pytest tests/ -v
cd catalog-service  && pytest tests/ -v
cd order-service    && pytest tests/ -v
cd payment-service  && pytest tests/ -v
cd api-gateway      && pytest tests/ -v

# Con cobertura
make test-cov

# Integración (levanta PostgreSQL en :5433 vía Docker)
make test-integration

# Smoke (requiere el stack completo levantado)
pytest tests_smoke/ -v
```

---

## Desarrollo frontend

```bash
cd frontend
pnpm install
pnpm dev          # → http://localhost:5173 (proxies /api/* → :8083)
pnpm build        # tsc -b && vite build
pnpm lint
```

---

## Notas de producción

| Aspecto | Detalle |
|---|---|
| **Montos** | `Numeric(14,2)` en todos los servicios — sin pérdida de precisión |
| **Stock** | Se reduce al crear la orden, no al pagar. Se restaura en cancelación/expiración |
| **Soft delete** | Los productos nunca se eliminan físicamente (`is_active=false`) |
| **Carrito** | `localStorage` — se limpia completamente al cerrar sesión |
| **Historial** | Cada cambio de estado de una orden queda en `order_service.order_history` |
| **Wompi real** | `WOMPI_TEST_MODE=false` + llaves de producción del dashboard de Wompi |
| **Pago real** | El gateway de pagos es Wompi Colombia (`wompi.co`) |

---

## Troubleshooting

**Contenedor `unhealthy`**
```bash
docker compose -f deploy/docker-compose.yml --env-file deploy/.env logs <servicio>
```
Causas más comunes: variable de entorno faltante, `DATABASE_URL` incorrecta, puerto 5432 en vez de 6543.

**401 en todas las peticiones**
- Verificar `SUPABASE_JWT_SECRET` en `deploy/.env`
- El gateway descarga JWKS de Supabase al arrancar: `make logs | grep -i jwks`

**Carrusel o paneles no aparecen en la home**
- Es normal si no hay contenido. Ir a `/admin/marketing` y subir imágenes de tipo `carousel` o `panel`.

**Base de datos: error de conexión**
- Usar Session Pooler de Supabase (puerto **6543**), no el Transaction Pooler (5432)
- Formato del usuario: `postgres.<project_ref>`
