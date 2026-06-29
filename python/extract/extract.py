"""
Extract – lê os CSVs de data/raw/ e faz upload para o MinIO (bucket: landing).
"""
import logging
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from python.config import (
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE,
    BUCKET_LANDING, DATA_RAW_PATH,
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


def ensure_bucket(client, bucket: str):
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)
        log.info(f"Bucket '{bucket}' criado.")


def upload_file(client, local_path: Path, bucket: str, object_name: str):
    client.upload_file(str(local_path), bucket, object_name)
    log.info(f"  Upload: {local_path.name} → s3://{bucket}/{object_name}")


def extract_to_landing():
    log.info("=== Extract: CSV → MinIO landing ===")
    client = get_s3_client()
    ensure_bucket(client, BUCKET_LANDING)

    raw_path = Path(DATA_RAW_PATH)
    csv_files = list(raw_path.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            f"Nenhum CSV encontrado em '{raw_path}'. "
            "Execute python/extract/generate_data.py primeiro."
        )

    for csv_file in csv_files:
        upload_file(client, csv_file, BUCKET_LANDING, f"ecommerce/{csv_file.name}")

    log.info(f"=== {len(csv_files)} arquivos enviados para s3://{BUCKET_LANDING}/ecommerce/ ===")


if __name__ == "__main__":
    extract_to_landing()
