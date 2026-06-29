{{ config(materialized='table', schema='gold') }}

SELECT
    category_name_english                               AS category,
    category_name                                       AS category_pt,

    COUNT(DISTINCT order_id)                            AS total_orders,
    COUNT(DISTINCT customer_id)                         AS unique_customers,
    SUM(price)                                          AS total_revenue,
    AVG(price)                                          AS avg_price,
    SUM(1)                                              AS units_sold,

    ROUND(
        100.0 * SUM(price) / NULLIF(SUM(SUM(price)) OVER (), 0),
        2
    )                                                   AS revenue_share_pct

FROM {{ ref('silver_order_items') }}
WHERE order_status = 'delivered'
  AND category_name IS NOT NULL
GROUP BY 1, 2
ORDER BY total_revenue DESC
