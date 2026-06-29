{{ config(materialized='table', schema='silver') }}

WITH orders_summary AS (
    SELECT
        o.customer_id,
        COUNT(DISTINCT o.order_id)                          AS total_orders,
        SUM(oi.price)                                       AS total_spent,
        AVG(oi.price)                                       AS avg_ticket,
        MIN(o.purchase_timestamp)                           AS first_order_at,
        MAX(o.purchase_timestamp)                           AS last_order_at,
        COUNT(DISTINCT DATE_TRUNC('month', o.purchase_timestamp)) AS active_months
    FROM {{ ref('bronze_orders') }} o
    JOIN {{ ref('bronze_order_items') }} oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY o.customer_id
)

SELECT
    c.customer_id,
    c.customer_unique_id,
    c.zip_code_prefix,
    c.city,
    c.state,

    -- Métricas de comportamento
    COALESCE(os.total_orders, 0)                            AS total_orders,
    COALESCE(os.total_spent, 0)                             AS total_spent,
    COALESCE(os.avg_ticket, 0)                              AS avg_ticket,
    os.first_order_at,
    os.last_order_at,

    -- Segmentação RFM simplificada
    CASE
        WHEN COALESCE(os.total_orders, 0) > 1  THEN true
        ELSE false
    END                                                     AS is_recurring,

    CASE
        WHEN COALESCE(os.total_spent, 0) >= 1000 THEN 'high_value'
        WHEN COALESCE(os.total_spent, 0) >= 300  THEN 'medium_value'
        WHEN COALESCE(os.total_spent, 0) > 0     THEN 'low_value'
        ELSE 'no_purchase'
    END                                                     AS customer_segment,

    c.created_at

FROM {{ ref('bronze_customers') }} c
LEFT JOIN orders_summary os ON c.customer_id = os.customer_id
