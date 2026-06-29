"""
Transform – lê Parquet do MinIO (bronze), aplica regras de negócio e salva em silver.
Usa Polars para processamento eficiente.
"""
import io
import logging
from pathlib import Path

import polars as pl
import boto3
from botocore.client import Config

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from python.config import (
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE,
    BUCKET_BRONZE, BUCKET_SILVER,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def get_s3_client():
    protocol = "https" if MINIO_SECURE else "http"
    return boto3.client(
        "s3",
        endpoint_url=f"{protocol}://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def read_parquet(client, bucket: str, key: str) -> pl.DataFrame:
    obj = client.get_object(Bucket=bucket, Key=key)
    return pl.read_parquet(io.BytesIO(obj["Body"].read()))


def write_parquet(client, df: pl.DataFrame, bucket: str, key: str):
    buf = io.BytesIO()
    df.write_parquet(buf)
    buf.seek(0)
    client.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
    log.info(f"  Salvo: s3://{bucket}/{key} ({len(df)} linhas)")


def transform_orders_with_items(client) -> pl.DataFrame:
    """Enriquece pedidos com totais dos itens e informação de entrega."""
    orders = read_parquet(client, BUCKET_BRONZE, "ecommerce/orders.parquet")
    items = read_parquet(client, BUCKET_BRONZE, "ecommerce/order_items.parquet")
    payments = read_parquet(client, BUCKET_BRONZE, "ecommerce/order_payments.parquet")

    # Agrega itens por pedido
    items_agg = items.group_by("order_id").agg([
        pl.col("price").sum().alias("items_total"),
        pl.col("freight_value").sum().alias("freight_total"),
        pl.len().alias("items_count"),
    ])

    # Agrega pagamentos por pedido
    payments_agg = payments.group_by("order_id").agg([
        pl.col("payment_value").sum().alias("payment_total"),
        pl.col("payment_type").first().alias("main_payment_type"),
        pl.col("payment_installments").max().alias("max_installments"),
    ])

    # Junta tudo
    enriched = (
        orders
        .join(items_agg, on="order_id", how="left")
        .join(payments_agg, on="order_id", how="left")
        .with_columns([
            (pl.col("items_total") + pl.col("freight_total")).alias("order_total"),
            # Dias para entrega
            pl.when(
                pl.col("delivered_customer_date").is_not_null() &
                pl.col("purchase_timestamp").is_not_null()
            )
            .then(
                (pl.col("delivered_customer_date") - pl.col("purchase_timestamp"))
                .dt.total_days()
            )
            .otherwise(None)
            .alias("delivery_days"),
            # Flag de entrega no prazo
            pl.when(
                pl.col("delivered_customer_date").is_not_null() &
                pl.col("estimated_delivery_date").is_not_null()
            )
            .then(
                pl.col("delivered_customer_date") <= pl.col("estimated_delivery_date")
            )
            .otherwise(None)
            .alias("delivered_on_time"),
            # Mês/ano de compra
            pl.col("purchase_timestamp").dt.year().alias("purchase_year"),
            pl.col("purchase_timestamp").dt.month().alias("purchase_month"),
        ])
    )
    return enriched


def transform_customers_with_metrics(client) -> pl.DataFrame:
    """Enriquece clientes com métricas de comportamento."""
    customers = read_parquet(client, BUCKET_BRONZE, "ecommerce/customers.parquet")
    orders = read_parquet(client, BUCKET_BRONZE, "ecommerce/orders.parquet")
    items = read_parquet(client, BUCKET_BRONZE, "ecommerce/order_items.parquet")

    items_agg = items.group_by("order_id").agg(
        pl.col("price").sum().alias("order_value")
    )

    orders_with_value = orders.join(items_agg, on="order_id", how="left")

    customer_metrics = (
        orders_with_value
        .filter(pl.col("order_status") == "delivered")
        .group_by("customer_id")
        .agg([
            pl.len().alias("total_orders"),
            pl.col("order_value").sum().alias("total_spent"),
            pl.col("order_value").mean().alias("avg_ticket"),
            pl.col("purchase_timestamp").max().alias("last_order_date"),
            pl.col("purchase_timestamp").min().alias("first_order_date"),
        ])
        .with_columns([
            pl.when(pl.col("total_orders") > 1).then(True).otherwise(False).alias("is_recurring"),
            # RFM simplificado: segmento por gasto total
            pl.when(pl.col("total_spent") >= 1000).then(pl.lit("high_value"))
            .when(pl.col("total_spent") >= 300).then(pl.lit("medium_value"))
            .otherwise(pl.lit("low_value"))
            .alias("customer_segment"),
        ])
    )

    return customers.join(customer_metrics, on="customer_id", how="left")


def transform_products_with_revenue(client) -> pl.DataFrame:
    """Enriquece produtos com receita gerada."""
    products = read_parquet(client, BUCKET_BRONZE, "ecommerce/products.parquet")
    categories = read_parquet(client, BUCKET_BRONZE, "ecommerce/product_categories.parquet")
    items = read_parquet(client, BUCKET_BRONZE, "ecommerce/order_items.parquet")
    orders = read_parquet(client, BUCKET_BRONZE, "ecommerce/orders.parquet")

    delivered_orders = orders.filter(pl.col("order_status") == "delivered").select("order_id")
    delivered_items = items.join(delivered_orders, on="order_id", how="inner")

    product_metrics = (
        delivered_items
        .group_by("product_id")
        .agg([
            pl.len().alias("units_sold"),
            pl.col("price").sum().alias("total_revenue"),
            pl.col("price").mean().alias("avg_price"),
        ])
    )

    return (
        products
        .join(product_metrics, on="product_id", how="left")
        .join(
            categories.rename({"product_category_name": "category_name"}),
            on="category_name",
            how="left"
        )
        .fill_null(0)
    )


def transform_all():
    log.info("=== Transform: bronze → silver ===")
    client = get_s3_client()

    log.info("Transformando pedidos...")
    orders_enriched = transform_orders_with_items(client)
    write_parquet(client, orders_enriched, BUCKET_SILVER, "ecommerce/orders_enriched.parquet")

    log.info("Transformando clientes...")
    customers_enriched = transform_customers_with_metrics(client)
    write_parquet(client, customers_enriched, BUCKET_SILVER, "ecommerce/customers_enriched.parquet")

    log.info("Transformando produtos...")
    products_enriched = transform_products_with_revenue(client)
    write_parquet(client, products_enriched, BUCKET_SILVER, "ecommerce/products_enriched.parquet")

    # Passa order_items sem transformação adicional (será feito no dbt)
    items = read_parquet(client, BUCKET_BRONZE, "ecommerce/order_items.parquet")
    write_parquet(client, items, BUCKET_SILVER, "ecommerce/order_items.parquet")

    log.info("=== Transformação concluída! Dados no bucket silver. ===")


if __name__ == "__main__":
    transform_all()
