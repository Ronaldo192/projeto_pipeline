{{ config(materialized='table', schema='gold') }}

SELECT
    purchase_month,
    purchase_year,
    purchase_month_num,

    COUNT(DISTINCT order_id)            AS total_orders,
    COUNT(DISTINCT customer_id)         AS unique_customers,
    SUM(items_total)                    AS total_revenue,
    SUM(freight_total)                  AS total_freight,
    SUM(payment_total)                  AS total_payment,

    AVG(items_total)                    AS avg_ticket,
    AVG(items_count)                    AS avg_items_per_order,

    SUM(CASE WHEN delivered_on_time THEN 1 ELSE 0 END)::FLOAT
        / NULLIF(COUNT(CASE WHEN delivered_on_time IS NOT NULL THEN 1 END), 0)
                                        AS on_time_delivery_rate,

    AVG(delivery_days)                  AS avg_delivery_days

FROM {{ ref('silver_orders') }}
WHERE order_status = 'delivered'
  AND items_total > 0
GROUP BY 1, 2, 3
ORDER BY 1
