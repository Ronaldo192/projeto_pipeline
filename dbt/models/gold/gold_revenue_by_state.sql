{{ config(materialized='table', schema='gold') }}

SELECT
    c.state,

    COUNT(DISTINCT o.order_id)          AS total_orders,
    COUNT(DISTINCT o.customer_id)       AS unique_customers,
    SUM(o.items_total)                  AS total_revenue,
    AVG(o.items_total)                  AS avg_ticket,
    SUM(o.freight_total)                AS total_freight,

    ROUND(
        100.0 * SUM(o.items_total) / NULLIF(SUM(SUM(o.items_total)) OVER (), 0),
        2
    )                                   AS revenue_share_pct

FROM {{ ref('silver_orders') }} o
JOIN {{ ref('silver_customers') }} c ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
  AND o.items_total > 0
GROUP BY 1
ORDER BY total_revenue DESC
