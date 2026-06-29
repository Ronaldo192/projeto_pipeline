{{ config(materialized='table', schema='bronze') }}

SELECT
    order_id,
    order_item_id,
    product_id,
    seller_id,
    shipping_limit_date,
    price,
    freight_value,
    price + freight_value AS item_total,
    created_at
FROM {{ source('raw', 'order_items') }}
WHERE order_id IS NOT NULL
  AND price > 0
