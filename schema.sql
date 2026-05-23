-- ============================================================
-- Papelería Boyacá v2 — Schema inicial
-- Ejecutado automáticamente por PostgreSQL al crear el contenedor
-- ============================================================

-- ── Extensiones ──────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- IDENTITY SERVICE
-- ============================================================
CREATE SCHEMA IF NOT EXISTS identity_service;

CREATE TABLE IF NOT EXISTS identity_service.roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(50)  UNIQUE NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS identity_service.users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name    VARCHAR(100) NOT NULL,
    last_name     VARCHAR(100) NOT NULL,
    document_id   VARCHAR(20)  UNIQUE,
    phone         VARCHAR(20),
    address       TEXT,
    city          VARCHAR(100),
    role_id       UUID         NOT NULL REFERENCES identity_service.roles(id),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    supabase_id   UUID,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_identity_users_email ON identity_service.users(email);

-- Roles iniciales
INSERT INTO identity_service.roles (name, description)
VALUES
    ('CLIENTE',    'Cliente de la tienda'),
    ('ADMIN',      'Gestiona catálogo, pedidos y transacciones'),
    ('SUPERADMIN', 'Acceso total al sistema')
ON CONFLICT (name) DO NOTHING;

-- Hook de Supabase: inyecta user_role en el JWT
-- Activar en: Supabase Dashboard → Authentication → Hooks → Custom Access Token
CREATE OR REPLACE FUNCTION identity_service.custom_access_token_hook(event jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
DECLARE role_name text;
BEGIN
    SELECT r.name INTO role_name
    FROM identity_service.users u
    JOIN identity_service.roles r ON r.id = u.role_id
    WHERE u.supabase_id = (event->>'user_id')::uuid;

    IF role_name IS NOT NULL THEN
        event := jsonb_set(event, '{claims,user_role}', to_jsonb(role_name));
    END IF;
    RETURN event;
END;
$$;

GRANT USAGE  ON SCHEMA identity_service              TO supabase_auth_admin;
GRANT EXECUTE ON FUNCTION identity_service.custom_access_token_hook TO supabase_auth_admin;
GRANT SELECT ON identity_service.users, identity_service.roles TO supabase_auth_admin;

-- ============================================================
-- CATALOG SERVICE
-- ============================================================
CREATE SCHEMA IF NOT EXISTS catalog_service;

CREATE TABLE IF NOT EXISTS catalog_service.categories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) NOT NULL,
    slug        VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_catalog_categories_name ON catalog_service.categories(name);

CREATE TABLE IF NOT EXISTS catalog_service.products (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku          VARCHAR(50)  UNIQUE NOT NULL,
    name         VARCHAR(255) NOT NULL,
    description  TEXT,
    price        FLOAT        NOT NULL,
    cost_price   FLOAT,
    stock        INTEGER      NOT NULL DEFAULT 0,
    category_id  UUID         NOT NULL REFERENCES catalog_service.categories(id),
    weight       FLOAT,
    dimensions   VARCHAR(100),
    sku_barcode  VARCHAR(100) UNIQUE,
    supplier_id  VARCHAR(100),
    image_url    VARCHAR(500),
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_catalog_products_sku  ON catalog_service.products(sku);
CREATE INDEX IF NOT EXISTS ix_catalog_products_name ON catalog_service.products(name);

-- ============================================================
-- ORDER SERVICE
-- ============================================================
CREATE SCHEMA IF NOT EXISTS order_service;

CREATE TABLE IF NOT EXISTS order_service.orders (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number        VARCHAR(50)  UNIQUE NOT NULL,
    user_id             UUID         NOT NULL,
    status              VARCHAR(20)  NOT NULL DEFAULT 'pending',
    subtotal            FLOAT        NOT NULL DEFAULT 0.0,
    tax_amount          FLOAT        NOT NULL DEFAULT 0,
    discount_percentage FLOAT        NOT NULL DEFAULT 0,
    discount_amount     FLOAT        NOT NULL DEFAULT 0,
    total               FLOAT        NOT NULL,
    shipping_address_id UUID,
    notes               TEXT,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_orders_order_number ON order_service.orders(order_number);
CREATE INDEX IF NOT EXISTS ix_orders_user_id      ON order_service.orders(user_id);
CREATE INDEX IF NOT EXISTS ix_orders_status       ON order_service.orders(status);

CREATE TABLE IF NOT EXISTS order_service.order_items (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id   UUID         NOT NULL REFERENCES order_service.orders(id),
    product_id UUID         NOT NULL,
    quantity   INTEGER      NOT NULL,
    unit_price FLOAT        NOT NULL,
    subtotal   FLOAT        NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_order_items_product_id ON order_service.order_items(product_id);

CREATE TABLE IF NOT EXISTS order_service.shipping_addresses (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID         NOT NULL,
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    city          VARCHAR(100) NOT NULL,
    postal_code   VARCHAR(20)  NOT NULL,
    is_default    BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_shipping_addresses_user_id ON order_service.shipping_addresses(user_id);

CREATE TABLE IF NOT EXISTS order_service.order_history (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id   UUID        NOT NULL REFERENCES order_service.orders(id),
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    changed_by UUID,
    notes      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- PAYMENT SERVICE
-- ============================================================
CREATE SCHEMA IF NOT EXISTS payment_service;

CREATE TABLE IF NOT EXISTS payment_service.transactions (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id             UUID         NOT NULL,
    user_id              UUID         NOT NULL,
    amount               FLOAT        NOT NULL,
    status               VARCHAR(20)  NOT NULL DEFAULT 'pending',
    payment_method       VARCHAR(50)  NOT NULL,
    wompi_reference      VARCHAR(100) UNIQUE,
    wompi_transaction_id VARCHAR(100),
    error_message        TEXT,
    meta                 JSONB,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_transactions_order_id ON payment_service.transactions(order_id);
CREATE INDEX IF NOT EXISTS ix_transactions_user_id  ON payment_service.transactions(user_id);
CREATE INDEX IF NOT EXISTS ix_transactions_status   ON payment_service.transactions(status);

CREATE TABLE IF NOT EXISTS payment_service.payment_methods (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID         NOT NULL,
    method_type      VARCHAR(50)  NOT NULL,
    reference        VARCHAR(255) NOT NULL,
    last_four_digits VARCHAR(4),
    card_brand       VARCHAR(50),
    expiry_date      VARCHAR(10),
    is_default       BOOLEAN      NOT NULL DEFAULT FALSE,
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_payment_methods_user_id ON payment_service.payment_methods(user_id);

CREATE TABLE IF NOT EXISTS payment_service.webhooks_log (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type       VARCHAR(100) NOT NULL,
    wompi_reference  VARCHAR(100),
    payload          JSONB        NOT NULL,
    processed        BOOLEAN      NOT NULL DEFAULT FALSE,
    error_message    TEXT,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
