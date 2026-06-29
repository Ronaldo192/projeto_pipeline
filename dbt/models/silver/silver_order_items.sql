{{ config(materialized='table', schema='silver') }}

SELECT
    oi.order_id,
    oi.order_item_id,
    oi.product_id,
    oi.seller_id,
    oi.shipping_limit_date,
    oi.price,
    oi.freight_value,
    oi.item_total,

    -- Enriquece com dados do produto
    p.category_name,
    p.category_name_english,
    p.weight_g,

    -- Contexto do pedido
    o.order_status,
    o.purchase_timestamp,
    o.customer_id,
    DATE_TRUNC('month', o.purchase_timestamp)::DATE AS purchase_month,

    oi.created_at

FROM {{ ref('bronze_order_items') }} oi
LEFT JOIN {{ ref('bronze_orders') }} o   ON oi.order_id = o.order_id
LEFT JOIN {{ ref('bronze_products') }} p ON oi.product_id = p.product_id
