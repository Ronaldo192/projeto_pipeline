{{ config(materialized='table', schema='gold') }}

-- KPIs consolidados para o dashboard executivo
WITH delivered_orders AS (
    SELECT * FROM {{ ref('silver_orders') }}
    WHERE order_status = 'delivered' AND items_total > 0
),

monthly AS (
    SELECT
        purchase_month,
        SUM(items_total) AS monthly_revenue
    FROM delivered_orders
    GROUP BY 1
),

monthly_growth AS (
    SELECT
        purchase_month,
        monthly_revenue,
        LAG(monthly_revenue) OVER (ORDER BY purchase_month) AS prev_month_revenue,
        ROUND(
            100.0 * (monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY purchase_month))
            / NULLIF(LAG(monthly_revenue) OVER (ORDER BY purchase_month), 0),
            2
        ) AS mom_growth_pct
    FROM monthly
)

SELECT
    -- Receita
    (SELECT SUM(items_total) FROM delivered_orders)             AS total_revenue,
    (SELECT AVG(items_total) FROM delivered_orders)             AS overall_avg_ticket,

    -- Pedidos
    (SELECT COUNT(DISTINCT order_id) FROM delivered_orders)     AS total_orders,
    (SELECT COUNT(DISTINCT customer_id) FROM delivered_orders)  AS total_customers,

    -- Clientes recorrentes
    (
        SELECT ROUND(100.0 * SUM(CASE WHEN is_recurring THEN 1 ELSE 0 END)::NUMERIC
                     / NULLIF(COUNT(*), 0), 2)
        FROM {{ ref('silver_customers') }}
        WHERE total_orders > 0
    )                                                           AS recurring_customers_pct,

    -- Crescimento no último mês completo
    (SELECT mom_growth_pct FROM monthly_growth ORDER BY purchase_month DESC LIMIT 1)
                                                                AS last_month_growth_pct,

    -- SLA de entrega
    (
        SELECT ROUND(100.0 * SUM(CASE WHEN delivered_on_time THEN 1 ELSE 0 END)::NUMERIC
                     / NULLIF(COUNT(CASE WHEN delivered_on_time IS NOT NULL THEN 1 END), 0), 2)
        FROM delivered_orders
    )                                                           AS on_time_delivery_pct,

    -- Tempo médio de entrega
    (SELECT ROUND(AVG(delivery_days), 1) FROM delivered_orders) AS avg_delivery_days,

    -- Categoria top
    (
        SELECT category
        FROM {{ ref('gold_revenue_by_category') }}
        ORDER BY total_revenue DESC
        LIMIT 1
    )                                                           AS top_category,

    -- Estado top
    (
        SELECT state
        FROM {{ ref('gold_revenue_by_state') }}
        ORDER BY total_revenue DESC
        LIMIT 1
    )                                                           AS top_state,

    NOW()                                                       AS calculated_at
