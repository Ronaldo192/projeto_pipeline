{{ config(materialized='table', schema='bronze') }}

SELECT
    customer_id,
    customer_unique_id,
    zip_code_prefix,
    city,
    state,
    created_at
FROM {{ source('raw', 'customers') }}
WHERE customer_id IS NOT NULL
