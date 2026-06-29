-- ============================================================
-- Inicialização do PostgreSQL
-- Banco: pipeline | Schemas: raw, bronze, silver, gold
-- ============================================================

-- Cria bancos auxiliares para Kestra e Metabase
CREATE DATABASE kestra;
CREATE DATABASE metabase;

-- Garante privilégios ao usuário pipeline
GRANT ALL PRIVILEGES ON DATABASE kestra TO pipeline;
GRANT ALL PRIVILEGES ON DATABASE metabase TO pipeline;

-- ============================================================
-- Schemas no banco pipeline (já conectado por POSTGRES_DB)
-- ============================================================
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

GRANT ALL ON SCHEMA raw     TO pipeline;
GRANT ALL ON SCHEMA bronze  TO pipeline;
GRANT ALL ON SCHEMA silver  TO pipeline;
GRANT ALL ON SCHEMA gold    TO pipeline;

-- ============================================================
-- Tabelas: schema raw (dados brutos carregados pelo Python)
-- ============================================================

CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id             VARCHAR(50)  PRIMARY KEY,
    customer_unique_id      VARCHAR(50),
    zip_code_prefix         VARCHAR(10),
    city                    VARCHAR(100),
    state                   CHAR(2),
    created_at              TIMESTAMP    DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.products (
    product_id              VARCHAR(50)  PRIMARY KEY,
    category_name           VARCHAR(100),
    name_length             INTEGER,
    description_length      INTEGER,
    photos_qty              INTEGER,
    weight_g                NUMERIC(10,2),
    length_cm               NUMERIC(8,2),
    height_cm               NUMERIC(8,2),
    width_cm                NUMERIC(8,2),
    created_at              TIMESTAMP    DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.orders (
    order_id                        VARCHAR(50)  PRIMARY KEY,
    customer_id                     VARCHAR(50),
    order_status                    VARCHAR(30),
    purchase_timestamp              TIMESTAMP,
    approved_at                     TIMESTAMP,
    delivered_carrier_date          TIMESTAMP,
    delivered_customer_date         TIMESTAMP,
    estimated_delivery_date         TIMESTAMP,
    created_at                      TIMESTAMP    DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.order_items (
    order_id                VARCHAR(50),
    order_item_id           INTEGER,
    product_id              VARCHAR(50),
    seller_id               VARCHAR(50),
    shipping_limit_date     TIMESTAMP,
    price                   NUMERIC(10,2),
    freight_value           NUMERIC(10,2),
    created_at              TIMESTAMP    DEFAULT NOW(),
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE IF NOT EXISTS raw.order_payments (
    order_id                VARCHAR(50),
    payment_sequential      INTEGER,
    payment_type            VARCHAR(30),
    payment_installments    INTEGER,
    payment_value           NUMERIC(10,2),
    created_at              TIMESTAMP    DEFAULT NOW(),
    PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE IF NOT EXISTS raw.product_categories (
    category_name           VARCHAR(100) PRIMARY KEY,
    category_name_english   VARCHAR(100)
);

-- ============================================================
-- Índices de performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_orders_customer    ON raw.orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status      ON raw.orders (order_status);
CREATE INDEX IF NOT EXISTS idx_orders_purchase    ON raw.orders (purchase_timestamp);
CREATE INDEX IF NOT EXISTS idx_items_order        ON raw.order_items (order_id);
CREATE INDEX IF NOT EXISTS idx_items_product      ON raw.order_items (product_id);
CREATE INDEX IF NOT EXISTS idx_payments_order     ON raw.order_payments (order_id);
