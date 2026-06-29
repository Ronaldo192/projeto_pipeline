"""
Load – lê Parquet do MinIO (silver/bronze) e carrega no PostgreSQL (schema raw).
Usa SQLAlchemy com upsert para idempotência.
"""
import io
import logging
from pathlib import Path

import polars as pl
import pandas as pd
import boto3
from botocore.client import Config
from sqlalchemy import create_engine, text

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from python.config import (
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE,
    BUCKET_BRONZE, POSTGRES_URL,
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


def read_parquet_from_minio(client, bucket: str, key: str) -> pd.DataFrame:
    obj = client.get_object(Bucket=bucket, Key=key)
    df_polars = pl.read_parquet(io.BytesIO(obj["Body"].read()))
    return df_polars.to_pandas()


def upsert_table(engine, df: pd.DataFrame, schema: str, table: str, pk_cols: list[str]):
    """Carrega dados usando staging table + INSERT ON CONFLICT."""
    staging = f"_staging_{table}"

    with engine.begin() as conn:
        # Cria staging temporária
        conn.execute(text(f"DROP TABLE IF EXISTS {schema}.{staging}"))
        conn.execute(text(f"CREATE TABLE {schema}.{staging} AS SELECT * FROM {schema}.{table} WHERE 1=0"))

        # Carrega dados no staging
        df.to_sql(staging, conn, schema=schema, if_exists="append", index=False, method="multi", chunksize=5000)

        # Constrói ON CONFLICT clause
        pk_list = ", ".join(pk_cols)
        non_pk = [c for c in df.columns if c not in pk_cols and c != "created_at"]
        update_set = ", ".join([f"{c} = EXCLUDED.{c}" for c in non_pk])

        upsert_sql = f"""
            INSERT INTO {schema}.{table}
            SELECT * FROM {schema}.{staging}
            ON CONFLICT ({pk_list}) DO UPDATE SET {update_set}
        """
        result = conn.execute(text(upsert_sql))
        conn.execute(text(f"DROP TABLE {schema}.{staging}"))

    log.info(f"  {schema}.{table}: {len(df)} linhas carregadas (upsert)")


LOAD_CONFIG = [
    ("ecommerce/customers.parquet",     "raw", "customers",     ["customer_id"]),
    ("ecommerce/products.parquet",      "raw", "products",      ["product_id"]),
    ("ecommerce/orders.parquet",        "raw", "orders",        ["order_id"]),
    ("ecommerce/order_items.parquet",   "raw", "order_items",   ["order_id", "order_item_id"]),
    ("ecommerce/order_payments.parquet","raw", "order_payments",["order_id", "payment_sequential"]),
    ("ecommerce/product_categories.parquet", "raw", "product_categories", ["product_category_name"]),
]


def load_all():
    log.info("=== Load: MinIO bronze → PostgreSQL raw ===")
    client = get_s3_client()
    engine = create_engine(POSTGRES_URL, pool_pre_ping=True)

    for minio_key, schema, table, pk_cols in LOAD_CONFIG:
        log.info(f"Carregando: {table}")
        try:
            df = read_parquet_from_minio(client, BUCKET_BRONZE, minio_key)
            upsert_table(engine, df, schema, table, pk_cols)
        except Exception as e:
            log.error(f"  Erro ao carregar {table}: {e}")
            raise

    engine.dispose()
    log.info("=== Carga concluída! Dados disponíveis no schema raw. ===")


if __name__ == "__main__":
    load_all()
