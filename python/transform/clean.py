"""
Clean – lê CSVs do MinIO (landing), aplica limpeza e salva como Parquet (bronze).
Usa Polars para alta performance.
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
    BUCKET_LANDING, BUCKET_BRONZE,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

VALID_STATES = {
    "SP", "RJ", "MG", "BA", "PR", "RS", "PE", "CE", "PA", "SC",
    "MA", "GO", "AM", "PB", "ES", "RN", "AL", "PI", "MT", "MS",
    "DF", "SE", "RO", "TO", "AC", "AP", "RR",
}

VALID_ORDER_STATUS = {"delivered", "shipped", "canceled", "invoiced", "processing", "approved"}
VALID_PAYMENT_TYPES = {"credit_card", "boleto", "voucher", "debit_card"}


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


def read_csv_from_minio(client, bucket: str, key: str) -> pl.DataFrame:
    obj = client.get_object(Bucket=bucket, Key=key)
    content = obj["Body"].read()
    return pl.read_csv(io.BytesIO(content), infer_schema_length=5000)


def write_parquet_to_minio(client, df: pl.DataFrame, bucket: str, key: str):
    buf = io.BytesIO()
    df.write_parquet(buf)
    buf.seek(0)
    client.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
    log.info(f"  Parquet salvo: s3://{bucket}/{key} ({len(df)} linhas)")


def clean_customers(df: pl.DataFrame) -> pl.DataFrame:
    original = len(df)
    # Cast para String primeiro — Polars pode inferir colunas numéricas como i64 ao ler CSV
    df = (
        df.drop_nulls(subset=["customer_id"])
        .unique(subset=["customer_id"])
        .with_columns([
            pl.col("city").cast(pl.Utf8).str.strip_chars().str.to_titlecase(),
            pl.col("state").cast(pl.Utf8).str.strip_chars().str.to_uppercase(),
            pl.col("zip_code_prefix").cast(pl.Utf8).str.strip_chars().str.zfill(8),
        ])
        .filter(pl.col("state").is_in(VALID_STATES))
    )
    log.info(f"  customers: {original} → {len(df)} linhas ({original - len(df)} removidas)")
    return df


def clean_orders(df: pl.DataFrame) -> pl.DataFrame:
    original = len(df)
    date_cols = ["purchase_timestamp", "approved_at", "delivered_carrier_date",
                 "delivered_customer_date", "estimated_delivery_date"]

    for col in date_cols:
        if col in df.columns:
            df = df.with_columns(
                pl.col(col).cast(pl.Utf8).str.to_datetime(strict=False)
            )

    df = (
        df.drop_nulls(subset=["order_id", "customer_id", "purchase_timestamp"])
        .unique(subset=["order_id"])
        .with_columns([
            pl.col("order_status").cast(pl.Utf8),
        ])
        .filter(pl.col("order_status").is_in(VALID_ORDER_STATUS))
    )
    log.info(f"  orders: {original} → {len(df)} linhas ({original - len(df)} removidas)")
    return df


def clean_products(df: pl.DataFrame) -> pl.DataFrame:
    original = len(df)
    numeric_cols = ["weight_g", "length_cm", "height_cm", "width_cm"]
    for col in numeric_cols:
        df = df.with_columns(pl.col(col).cast(pl.Float64, strict=False))

    df = (
        df.drop_nulls(subset=["product_id"])
        .unique(subset=["product_id"])
        .filter(pl.col("weight_g") > 0)
    )
    log.info(f"  products: {original} → {len(df)} linhas ({original - len(df)} removidas)")
    return df


def clean_order_items(df: pl.DataFrame) -> pl.DataFrame:
    original = len(df)
    df = (
        df.drop_nulls(subset=["order_id", "product_id"])
        .unique(subset=["order_id", "order_item_id"])
        .with_columns([
            pl.col("price").cast(pl.Float64, strict=False),
            pl.col("freight_value").cast(pl.Float64, strict=False),
        ])
        .filter((pl.col("price") > 0) & (pl.col("freight_value") >= 0))
    )
    log.info(f"  order_items: {original} → {len(df)} linhas ({original - len(df)} removidas)")
    return df


def clean_order_payments(df: pl.DataFrame) -> pl.DataFrame:
    original = len(df)
    df = (
        df.drop_nulls(subset=["order_id"])
        .unique(subset=["order_id", "payment_sequential"])
        .with_columns(pl.col("payment_type").cast(pl.Utf8))
        .filter(pl.col("payment_type").is_in(VALID_PAYMENT_TYPES))
        .with_columns([
            pl.col("payment_value").cast(pl.Float64, strict=False),
            pl.col("payment_installments").cast(pl.Int32, strict=False),
        ])
        .filter(pl.col("payment_value") > 0)
    )
    log.info(f"  order_payments: {original} → {len(df)} linhas ({original - len(df)} removidas)")
    return df


CLEANING_MAP = {
    "ecommerce/customers.csv": ("customers", clean_customers),
    "ecommerce/orders.csv": ("orders", clean_orders),
    "ecommerce/products.csv": ("products", clean_products),
    "ecommerce/order_items.csv": ("order_items", clean_order_items),
    "ecommerce/order_payments.csv": ("order_payments", clean_order_payments),
    "ecommerce/product_categories.csv": ("product_categories", lambda df: df),
}


def clean_all():
    log.info("=== Clean: landing → bronze (Parquet) ===")
    client = get_s3_client()

    for source_key, (table_name, clean_fn) in CLEANING_MAP.items():
        log.info(f"Processando: {table_name}")
        try:
            df = read_csv_from_minio(client, BUCKET_LANDING, source_key)
            df_clean = clean_fn(df)
            write_parquet_to_minio(client, df_clean, BUCKET_BRONZE, f"ecommerce/{table_name}.parquet")
        except Exception as e:
            log.error(f"  Erro em {table_name}: {e}")
            raise

    log.info("=== Limpeza concluída! Dados no bucket bronze. ===")


if __name__ == "__main__":
    clean_all()
