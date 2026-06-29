{{ config(materialized='table', schema='bronze') }}

SELECT
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value,
    created_at
FROM {{ source('raw', 'order_payments') }}
WHERE order_id IS NOT NULL
  AND payment_value > 0
