# Data Engineering Pipeline — E-commerce

Pipeline completo de engenharia de dados simulando um e-commerce brasileiro. Projeto de portfólio com stack moderna e fluxo end-to-end: ingestão → transformação → visualização.

## Arquitetura

```
GitHub → GitHub Actions (CI/CD)
              │
         Docker Compose
              │
    ┌─────────┴──────────────────────┐
    │         Kestra (Orquestração)  │
    └─────────┬──────────────────────┘
              │
   ┌──────────┼──────────┬───────────┐
   ▼          ▼          ▼           ▼
Python     MinIO      PostgreSQL  Metabase
(ETL)    (Data Lake) (OLTP/DWH)  (Dashboard)
           │              │
    landing│              │ raw
    bronze │              │ bronze
    silver │    dbt       │ silver
    gold   │──────────────│ gold
                          │
                          ▼
                      Metabase
                   (schema gold)
```

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Orquestração | [Kestra](https://kestra.io/) |
| Processamento | Python 3.11 (Pandas + Polars) |
| Object Storage | MinIO (S3-compatible) |
| Banco de dados | PostgreSQL 15 |
| Transformação | dbt-core + dbt-postgres |
| Visualização | Metabase |
| CI/CD | GitHub Actions |
| Containers | Docker Compose |

## Estrutura do Projeto

```
data-engineering-pipeline/
├── .github/workflows/ci.yml   # CI/CD: lint → test → build → dbt validate
├── docker/
│   └── Dockerfile.python      # Imagem Python worker + dbt
├── kestra/flows/
│   └── pipeline_ecommerce.yml # Fluxo de orquestração
├── python/
│   ├── config.py              # Configurações centralizadas
│   ├── extract/
│   │   ├── generate_data.py   # Gerador de dados sintéticos
│   │   └── extract.py         # CSV → MinIO landing
│   ├── transform/
│   │   ├── clean.py           # landing → bronze (Parquet)
│   │   └── transform.py       # bronze → silver (regras de negócio)
│   ├── load/
│   │   └── load.py            # silver → PostgreSQL raw
│   └── tests/
│       └── test_pipeline.py   # Testes unitários
├── dbt/
│   ├── models/
│   │   ├── bronze/            # Limpeza mínima do raw
│   │   ├── silver/            # Regras de negócio
│   │   └── gold/              # Agregações para dashboard
│   └── macros/
│       └── generate_schema_name.sql
├── postgres/
│   └── init.sql               # Schemas e tabelas iniciais
├── data/
│   ├── raw/                   # CSVs gerados
│   ├── bronze/                # Parquet limpo
│   ├── silver/                # Parquet transformado
│   └── gold/                  # Parquet para análise
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Fluxo de dados

```
generate_data.py → data/raw/ (CSV)
        ↓
extract.py → MinIO: landing/ecommerce/*.csv
        ↓
clean.py → MinIO: bronze/ecommerce/*.parquet
        ↓
transform.py → MinIO: silver/ecommerce/*.parquet
        ↓
load.py → PostgreSQL: schema raw
        ↓
dbt run → raw → bronze → silver → gold
        ↓
Metabase → schema gold
```

## Modelos dbt

### Bronze — limpeza e tipagem
- `bronze_customers` — clientes sem nulos, estados válidos
- `bronze_orders` — pedidos a partir de 2022-01-01
- `bronze_order_items` — itens com total calculado
- `bronze_order_payments` — pagamentos válidos
- `bronze_products` — produtos com categoria em inglês

### Silver — regras de negócio
- `silver_customers` — segmento RFM, flag de recorrência, métricas de comportamento
- `silver_orders` — SLA de entrega, forma de pagamento principal, totais
- `silver_order_items` — enriquecido com produto e contexto do pedido

### Gold — métricas para dashboard
- `gold_revenue_by_month` — receita mensal com crescimento MoM
- `gold_revenue_by_category` — receita por categoria com market share
- `gold_revenue_by_state` — receita por estado brasileiro
- `gold_top_products` — top 100 produtos
- `gold_top_customers` — top 100 clientes
- `gold_kpis` — painel consolidado (receita total, ticket médio, % on-time, etc.)

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 4.x+
- Git

## Início rápido

### 1. Clonar e configurar

```bash
git clone <seu-repositorio>
cd data-engineering-pipeline

cp .env.example .env
```

### 2. Build da imagem Python

```bash
docker build -t pipeline-python:latest -f docker/Dockerfile.python .
```

### 3. Subir os serviços

```bash
docker compose up -d
```

Aguarde ~60 segundos para todos os serviços inicializarem.

### 4. Executar o pipeline manualmente

```bash
# Dentro do container Python worker
docker exec -it pipeline_python bash

# Passo a passo
python python/extract/generate_data.py
python python/extract/extract.py
python python/transform/clean.py
python python/transform/transform.py
python python/load/load.py

# dbt
cd dbt
dbt deps
dbt run
dbt test
```

### 5. Executar via Kestra

1. Acesse `http://localhost:8080`
2. Vá em **Flows** → `data_engineering` → `ecommerce_pipeline`
3. Clique em **Execute**

### 6. Visualizar no Metabase

1. Acesse `http://localhost:3000`
2. Configure a conexão PostgreSQL:
   - Host: `postgres`
   - Porta: `5432`
   - Banco: `pipeline`
   - Schema: `gold`
   - Usuário: `pipeline`
   - Senha: `pipeline123`

## Serviços e portas

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| Kestra UI | http://localhost:8080 | — |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin123 |
| Metabase | http://localhost:3000 | (configurar no primeiro acesso) |
| PostgreSQL | localhost:5432 | pipeline / pipeline123 |

## Testes

```bash
# Testes unitários Python
pytest python/tests/ -v --cov=python

# Testes dbt
cd dbt && dbt test
```

## CI/CD (GitHub Actions)

O workflow `.github/workflows/ci.yml` executa automaticamente em todo push:

1. **Lint** — Black + isort + Flake8
2. **Testes unitários** — pytest com cobertura
3. **Build Docker** — valida o Dockerfile
4. **dbt validate** — `dbt parse` contra PostgreSQL temporário
5. **Deploy info** — (extensível para deploy real)

## Branches

```
main        ← produção (protegida)
develop     ← integração
feature/*   ← funcionalidades
```

## Dashboard — Indicadores disponíveis no schema `gold`

- Receita total
- Ticket médio
- Total de pedidos e clientes únicos
- % de entregas no prazo
- Tempo médio de entrega
- Crescimento mensal (MoM)
- Top 10 categorias por receita
- Top 10 estados por receita
- Top 10 produtos
- Top 10 clientes
- % clientes recorrentes
- Market share por categoria

---

Projeto desenvolvido como portfólio de engenharia de dados.
