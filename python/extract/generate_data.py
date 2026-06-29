"""
Gerador de dados sintéticos de e-commerce.
Cria CSVs realistas com dados brasileiros usando Faker.
"""
import os
import random
import logging
from pathlib import Path

import pandas as pd
from faker import Faker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

fake = Faker("pt_BR")
random.seed(42)

DATA_RAW_PATH = Path("data/raw")

CATEGORIES = [
    ("beleza_saude", "health_beauty"),
    ("informatica_acessorios", "computers_accessories"),
    ("automotivo", "auto"),
    ("cama_mesa_banho", "bed_bath_table"),
    ("moveis_decoracao", "furniture_decor"),
    ("esporte_lazer", "sports_leisure"),
    ("perfumaria", "perfumery"),
    ("utilidades_domesticas", "housewares"),
    ("telefonia", "telephony"),
    ("relogios_presentes", "watches_gifts"),
    ("alimentos_bebidas", "food_drink"),
    ("brinquedos", "toys"),
    ("cool_stuff", "cool_stuff"),
    ("ferramentas_jardim", "garden_tools"),
    ("fashion_bolsas_e_acessorios", "fashion_bags_accessories"),
    ("eletroportateis", "small_appliances"),
    ("eletronicos", "electronics"),
    ("eletrodomesticos", "home_appliances"),
    ("livros_interesse_geral", "books_general"),
    ("construcao_ferramentas_construcao", "construction_tools_construction"),
]

ESTADOS_BR = [
    "SP", "RJ", "MG", "BA", "PR", "RS", "PE", "CE", "PA",
    "SC", "MA", "GO", "AM", "PB", "ES", "RN", "AL", "PI",
    "MT", "MS", "DF", "SE", "RO", "TO", "AC", "AP", "RR",
]

STATUS_PEDIDO = ["delivered", "shipped", "canceled", "invoiced", "processing", "approved"]
STATUS_PESO = [0.70, 0.15, 0.05, 0.04, 0.03, 0.03]

FORMAS_PAGAMENTO = ["credit_card", "boleto", "voucher", "debit_card"]
PAGAMENTO_PESO = [0.73, 0.19, 0.05, 0.03]


def _ensure_dir():
    DATA_RAW_PATH.mkdir(parents=True, exist_ok=True)


def generate_categories() -> pd.DataFrame:
    log.info("Gerando categorias...")
    df = pd.DataFrame(CATEGORIES, columns=["product_category_name", "product_category_name_english"])
    df.to_csv(DATA_RAW_PATH / "product_categories.csv", index=False)
    log.info(f"  {len(df)} categorias criadas")
    return df


def generate_customers(n: int = 10_000) -> pd.DataFrame:
    log.info(f"Gerando {n} clientes...")
    records = []
    for _ in range(n):
        state = random.choice(ESTADOS_BR)
        records.append({
            "customer_id": fake.uuid4(),
            "customer_unique_id": fake.uuid4(),
            "zip_code_prefix": str(fake.postcode()).replace("-", "")[:8],
            "city": fake.city(),
            "state": state,
        })
    df = pd.DataFrame(records)
    df.to_csv(DATA_RAW_PATH / "customers.csv", index=False)
    log.info(f"  {len(df)} clientes criados")
    return df


def generate_products(n: int = 5_000) -> pd.DataFrame:
    log.info(f"Gerando {n} produtos...")
    records = []
    for _ in range(n):
        cat = random.choice(CATEGORIES)[0]
        records.append({
            "product_id": fake.uuid4(),
            "category_name": cat,
            "name_length": random.randint(20, 80),
            "description_length": random.randint(100, 3000),
            "photos_qty": random.randint(1, 10),
            "weight_g": round(random.uniform(50, 30000), 2),
            "length_cm": round(random.uniform(10, 100), 2),
            "height_cm": round(random.uniform(5, 80), 2),
            "width_cm": round(random.uniform(8, 90), 2),
        })
    df = pd.DataFrame(records)
    df.to_csv(DATA_RAW_PATH / "products.csv", index=False)
    log.info(f"  {len(df)} produtos criados")
    return df


def generate_orders(customers: pd.DataFrame, n: int = 50_000) -> pd.DataFrame:
    log.info(f"Gerando {n} pedidos...")
    customer_ids = customers["customer_id"].tolist()
    records = []

    for _ in range(n):
        purchase_dt = fake.date_time_between(start_date="-2y", end_date="now")
        status = random.choices(STATUS_PEDIDO, weights=STATUS_PESO)[0]

        approved = purchase_dt + pd.Timedelta(hours=random.randint(1, 48)) if status != "canceled" else None
        carrier_date = approved + pd.Timedelta(days=random.randint(1, 5)) if approved and status in ("delivered", "shipped") else None
        delivery_date = carrier_date + pd.Timedelta(days=random.randint(1, 15)) if carrier_date and status == "delivered" else None
        estimated = purchase_dt + pd.Timedelta(days=random.randint(5, 30))

        records.append({
            "order_id": fake.uuid4(),
            "customer_id": random.choice(customer_ids),
            "order_status": status,
            "purchase_timestamp": purchase_dt,
            "approved_at": approved,
            "delivered_carrier_date": carrier_date,
            "delivered_customer_date": delivery_date,
            "estimated_delivery_date": estimated,
        })

    df = pd.DataFrame(records)
    df.to_csv(DATA_RAW_PATH / "orders.csv", index=False)
    log.info(f"  {len(df)} pedidos criados")
    return df


def generate_order_items(orders: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    log.info("Gerando itens de pedido...")
    order_ids = orders["order_id"].tolist()
    product_ids = products["product_id"].tolist()
    records = []

    for order_id in order_ids:
        n_items = random.choices([1, 2, 3, 4, 5], weights=[0.60, 0.25, 0.10, 0.03, 0.02])[0]
        for seq in range(1, n_items + 1):
            records.append({
                "order_id": order_id,
                "order_item_id": seq,
                "product_id": random.choice(product_ids),
                "seller_id": fake.uuid4(),
                "shipping_limit_date": fake.date_time_between(start_date="-2y", end_date="now"),
                "price": round(random.uniform(9.90, 2500.00), 2),
                "freight_value": round(random.uniform(5.00, 80.00), 2),
            })

    df = pd.DataFrame(records)
    df.to_csv(DATA_RAW_PATH / "order_items.csv", index=False)
    log.info(f"  {len(df)} itens criados")
    return df


def generate_order_payments(orders: pd.DataFrame) -> pd.DataFrame:
    log.info("Gerando pagamentos...")
    records = []

    for order_id in orders["order_id"]:
        payment_type = random.choices(FORMAS_PAGAMENTO, weights=PAGAMENTO_PESO)[0]
        installments = random.choices(range(1, 13), weights=[0.40, 0.20, 0.10, 0.08, 0.06, 0.05, 0.03, 0.02, 0.02, 0.01, 0.01, 0.02])[0]
        value = round(random.uniform(10.00, 5000.00), 2)

        records.append({
            "order_id": order_id,
            "payment_sequential": 1,
            "payment_type": payment_type,
            "payment_installments": installments,
            "payment_value": value,
        })

    df = pd.DataFrame(records)
    df.to_csv(DATA_RAW_PATH / "order_payments.csv", index=False)
    log.info(f"  {len(df)} pagamentos criados")
    return df


def generate_all_data():
    _ensure_dir()
    log.info("=== Iniciando geração de dados sintéticos ===")

    categories = generate_categories()
    customers = generate_customers(10_000)
    products = generate_products(5_000)
    orders = generate_orders(customers, 50_000)
    generate_order_items(orders, products)
    generate_order_payments(orders)

    log.info("=== Dados gerados com sucesso! ===")
    log.info(f"Arquivos salvos em: {DATA_RAW_PATH.resolve()}")


if __name__ == "__main__":
    generate_all_data()
