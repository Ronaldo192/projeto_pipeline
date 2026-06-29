{{ config(materialized='table', schema='bronze') }}

SELECT
    order_id,
    customer_id,
    order_status,
    purchase_timestamp,
    approved_at,
    delivered_carrier_date,
    delivered_customer_date,
    estimated_delivery_date,
    created_at
FROM {{ source('raw', 'orders') }}
WHERE order_id IS NOT NULL
  AND purchase_timestamp >= '{{ var("min_order_date") }}'
