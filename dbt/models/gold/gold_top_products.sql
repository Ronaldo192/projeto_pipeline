{{ config(materialized='table', schema='gold') }}

WITH product_sales AS (
    SELECT
        oi.product_id,
        p.category_name_english                             AS category,
        COUNT(DISTINCT oi.order_id)                         AS total_orders,
        SUM(oi.price)                                       AS total_revenue,
        COUNT(*)                                            AS units_sold,
        AVG(oi.price)                                       AS avg_price,
        MIN(oi.price)                                       AS min_price,
        MAX(oi.price)                                       AS max_price
    FROM {{ ref('silver_order_items') }} oi
    LEFT JOIN {{ ref('bronze_products') }} p ON oi.product_id = p.product_id
    WHERE oi.order_status = 'delivered'
    GROUP BY 1, 2
)

SELECT
    product_id,
    category,
    total_orders,
    total_revenue,
    units_sold,
    avg_price,
    min_price,
    max_price,
    RANK() OVER (ORDER BY total_revenue DESC)   AS revenue_rank,
    RANK() OVER (ORDER BY units_sold DESC)      AS units_rank
FROM product_sales
ORDER BY revenue_rank
LIMIT 100
