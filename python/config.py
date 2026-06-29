import os
from dotenv import load_dotenv

load_dotenv()

# ── PostgreSQL ────────────────────────────────────────────────
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "pipeline")
POSTGRES_USER = os.getenv("POSTGRES_USER", "pipeline")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "pipeline123")
POSTGRES_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# ── MinIO ─────────────────────────────────────────────────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

# ── Buckets MinIO ─────────────────────────────────────────────
BUCKET_LANDING = "landing"
BUCKET_BRONZE = "bronze"
BUCKET_SILVER = "silver"
BUCKET_GOLD = "gold"

# ── Caminhos locais ───────────────────────────────────────────
DATA_RAW_PATH = "data/raw"
DATA_BRONZE_PATH = "data/bronze"
DATA_SILVER_PATH = "data/silver"
DATA_GOLD_PATH = "data/gold"

# ── Logging ───────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
