{{ config(materialized='table', schema='bronze') }}

SELECT
    p.product_id,
    p.category_name,
    COALESCE(pc.category_name_english, p.category_name) AS category_name_english,
    p.name_length,
    p.description_length,
    p.photos_qty,
    p.weight_g,
    p.length_cm,
    p.height_cm,
    p.width_cm,
    p.created_at
FROM {{ source('raw', 'products') }} p
LEFT JOIN {{ source('raw', 'product_categories') }} pc
    ON p.category_name = pc.product_category_name
WHERE p.product_id IS NOT NULL
