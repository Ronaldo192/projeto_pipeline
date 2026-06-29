"""
Testes unitários do pipeline de e-commerce.
"""
import io
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


# ── Testes: generate_data ──────────────────────────────────────
class TestGenerateData:
    def test_generate_customers_schema(self, tmp_path):
        from python.extract.generate_data import generate_customers
        with patch("python.extract.generate_data.DATA_RAW_PATH", tmp_path):
            df = generate_customers(n=100)
        assert len(df) == 100
        assert "customer_id" in df.columns
        assert "state" in df.columns
        assert df["customer_id"].nunique() == 100

    def test_generate_products_schema(self, tmp_path):
        from python.extract.generate_data import generate_products
        with patch("python.extract.generate_data.DATA_RAW_PATH", tmp_path):
            df = generate_products(n=50)
        assert len(df) == 50
        assert "product_id" in df.columns
        assert "weight_g" in df.columns
        assert (df["weight_g"] > 0).all()

    def test_generate_orders_links_to_customers(self, tmp_path):
        from python.extract.generate_data import generate_customers, generate_orders
        with patch("python.extract.generate_data.DATA_RAW_PATH", tmp_path):
            customers = generate_customers(n=100)
            orders = generate_orders(customers, n=200)

        valid_customer_ids = set(customers["customer_id"])
        assert all(cid in valid_customer_ids for cid in orders["customer_id"])


# ── Testes: clean ─────────────────────────────────────────────
class TestClean:
    def test_clean_customers_removes_nulls(self):
        from python.transform.clean import clean_customers
        df = pl.DataFrame({
            "customer_id": ["id1", None, "id3", "id1"],
            "customer_unique_id": ["u1", "u2", "u3", "u4"],
            "zip_code_prefix": ["12345", "67890", "11111", "12345"],
            "city": ["são paulo", "rio", "belo horizonte", "são paulo"],
            "state": ["SP", "RJ", "MG", "SP"],
        })
        result = clean_customers(df)
        assert None not in result["customer_id"].to_list()
        assert len(result) == 2  # sem null, sem duplicata

    def test_clean_customers_normalizes_state(self):
        from python.transform.clean import clean_customers
        df = pl.DataFrame({
            "customer_id": ["id1"],
            "customer_unique_id": ["u1"],
            "zip_code_prefix": ["12345678"],
            "city": ["São Paulo"],
            "state": ["sp"],
        })
        result = clean_customers(df)
        assert result["state"][0] == "SP"

    def test_clean_customers_filters_invalid_state(self):
        from python.transform.clean import clean_customers
        df = pl.DataFrame({
            "customer_id": ["id1", "id2"],
            "customer_unique_id": ["u1", "u2"],
            "zip_code_prefix": ["12345", "67890"],
            "city": ["Cidade A", "Cidade B"],
            "state": ["SP", "XX"],  # XX é inválido
        })
        result = clean_customers(df)
        assert len(result) == 1
        assert result["state"][0] == "SP"

    def test_clean_order_payments_filters_invalid_type(self):
        from python.transform.clean import clean_order_payments
        df = pl.DataFrame({
            "order_id": ["o1", "o2"],
            "payment_sequential": [1, 1],
            "payment_type": ["credit_card", "crypto"],  # crypto inválido
            "payment_installments": [1, 1],
            "payment_value": [100.0, 50.0],
        })
        result = clean_order_payments(df)
        assert len(result) == 1
        assert result["payment_type"][0] == "credit_card"

    def test_clean_products_filters_zero_weight(self):
        from python.transform.clean import clean_products
        df = pl.DataFrame({
            "product_id": ["p1", "p2"],
            "category_name": ["eletronicos", "brinquedos"],
            "name_length": [30, 40],
            "description_length": [200, 300],
            "photos_qty": [3, 2],
            "weight_g": [0.0, 500.0],
            "length_cm": [10.0, 20.0],
            "height_cm": [5.0, 8.0],
            "width_cm": [8.0, 12.0],
        })
        result = clean_products(df)
        assert len(result) == 1
        assert result["product_id"][0] == "p2"


# ── Testes: config ────────────────────────────────────────────
class TestConfig:
    def test_postgres_url_format(self):
        from python.config import POSTGRES_URL
        assert POSTGRES_URL.startswith("postgresql://")
        assert "@" in POSTGRES_URL

    def test_bucket_names_defined(self):
        from python.config import BUCKET_LANDING, BUCKET_BRONZE, BUCKET_SILVER, BUCKET_GOLD
        assert BUCKET_LANDING == "landing"
        assert BUCKET_BRONZE == "bronze"
        assert BUCKET_SILVER == "silver"
        assert BUCKET_GOLD == "gold"
