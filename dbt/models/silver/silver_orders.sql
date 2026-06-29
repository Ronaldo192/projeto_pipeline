{{ config(materialized='table', schema='silver') }}

WITH items_agg AS (
    SELECT
        order_id,
        COUNT(*)            AS items_count,
        SUM(price)          AS items_total,
        SUM(freight_value)  AS freight_total,
        SUM(item_total)     AS order_subtotal
    FROM {{ ref('bronze_order_items') }}
    GROUP BY order_id
),

payments_agg AS (
    SELECT
        order_id,
        SUM(payment_value)              AS payment_total,
        MAX(payment_installments)       AS max_installments,
        -- Forma de pagamento principal (maior valor)
        (ARRAY_AGG(payment_type ORDER BY payment_value DESC))[1] AS main_payment_type
    FROM {{ ref('bronze_order_payments') }}
    GROUP BY order_id
)

SELECT
    o.order_id,
    o.customer_id,
    o.order_status,
    o.purchase_timestamp,
    o.approved_at,
    o.delivered_carrier_date,
    o.delivered_customer_date,
    o.estimated_delivery_date,

    -- Datas derivadas
    DATE_TRUNC('month', o.purchase_timestamp)::DATE         AS purchase_month,
    EXTRACT(YEAR FROM o.purchase_timestamp)::INT            AS purchase_year,
    EXTRACT(MONTH FROM o.purchase_timestamp)::INT           AS purchase_month_num,
    EXTRACT(DOW FROM o.purchase_timestamp)::INT             AS purchase_dow,

    -- Financeiro
    COALESCE(ia.items_total, 0)                             AS items_total,
    COALESCE(ia.freight_total, 0)                           AS freight_total,
    COALESCE(ia.order_subtotal, 0)                          AS order_subtotal,
    COALESCE(pa.payment_total, 0)                           AS payment_total,
    COALESCE(ia.items_count, 0)                             AS items_count,

    -- Pagamento
    pa.main_payment_type,
    COALESCE(pa.max_installments, 1)                        AS max_installments,

    -- SLA de entrega
    CASE
        WHEN o.delivered_customer_date IS NOT NULL AND o.purchase_timestamp IS NOT NULL
        THEN EXTRACT(EPOCH FROM (o.delivered_customer_date - o.purchase_timestamp)) / 86400
    END::INT                                                AS delivery_days,

    CASE
        WHEN o.delivered_customer_date IS NOT NULL AND o.estimated_delivery_date IS NOT NULL
        THEN o.delivered_customer_date <= o.estimated_delivery_date
    END                                                     AS delivered_on_time,

    o.created_at

FROM {{ ref('bronze_orders') }} o
LEFT JOIN items_agg ia      ON o.order_id = ia.order_id
LEFT JOIN payments_agg pa   ON o.order_id = pa.order_id
