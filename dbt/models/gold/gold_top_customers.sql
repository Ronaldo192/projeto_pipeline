{{ config(materialized='table', schema='gold') }}

SELECT
    c.customer_id,
    c.city,
    c.state,
    c.customer_segment,
    c.is_recurring,

    c.total_orders,
    c.total_spent,
    c.avg_ticket,
    c.first_order_at,
    c.last_order_at,

    -- Dias desde o último pedido (recência)
    EXTRACT(DAY FROM (NOW() - c.last_order_at))::INT        AS days_since_last_order,

    -- Período ativo em dias
    EXTRACT(DAY FROM (c.last_order_at - c.first_order_at))::INT AS customer_lifespan_days,

    RANK() OVER (ORDER BY c.total_spent DESC)               AS spending_rank

FROM {{ ref('silver_customers') }} c
WHERE c.total_orders > 0
ORDER BY spending_rank
LIMIT 100
