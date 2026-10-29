# E-Commerce End-to-End Data Engineering Pipeline

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Database](https://img.shields.io/badge/Data%20Warehouse-PostgreSQL%20%7C%20SQLite-green.svg)](https://www.postgresql.org/)
[![Orchestration](https://img.shields.io/badge/Orchestration-Apache%20Airflow-red.svg)](https://airflow.apache.org/)
[![BI](https://img.shields.io/badge/BI%20Dashboard-Power%20BI-yellow.svg)](https://powerbi.microsoft.com/)
[![Tests](https://img.shields.io/badge/Tests-Pytest%20(8%2F8%20Passed)-brightgreen.svg)](https://pytest.org/)
[![Design](https://img.shields.io/badge/Architecture-Kimball%20Star%20Schema%20%2B%20SCD%20Type%202-orange.svg)](#)

An enterprise-grade, production-ready Data Engineering project demonstrating how raw, multi-source e-commerce transactional data is ingested, cleansed, validated, and modeled into an analytical **Kimball Star Schema Data Warehouse** with **Slowly Changing Dimensions (SCD Type 2)**, **Incremental Watermark Loading**, **Automated Data Quality Audits**, **Airflow DAG Orchestration**, and a **Power BI Semantic Reporting Layer**.

---

## Architecture Flow

```
                      +---------------------------------------+
                      |       Raw E-Commerce Sources          |
                      | (Customers, Products, Orders, Items,  |
                      |        Payments, Returns)             |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |         Data Ingestion Layer          |
                      |  - Schema & Column Validation         |
                      |  - Batch Staging                      |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |      Data Cleaning & Sanitization     |
                      |  - Deduplication & Whitespace Strip   |
                      |  - Phone & Email Normalization        |
                      |  - Price & Math Consistency Checks    |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |    Kimball Dimensional Modeling       |
                      |  - dim_customer (SCD Type 2)          |
                      |  - dim_product  (SCD Type 1)          |
                      |  - dim_date     (Role-Playing)        |
                      |  - dim_payment_method / order_status  |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |      Incremental Loading Engine       |
                      |  - Watermark Timestamp Tracking       |
                      |  - Point-in-Time Surrogate Key Lookup |
                      |  - fact_sales & fact_returns Upsert   |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |    Automated Data Quality Audit       |
                      |  - Uniqueness, FK Null & Orphan Check |
                      |  - SCD2 Single-Active Version Check   |
                      |  - Financial Reconciliation Equations |
                      +-------------------+-------------------+
                                          |
                    +---------------------+---------------------+
                    |                                           |
                    v                                           v
      +----------------------------+             +----------------------------+
      |  Advanced SQL Analytics    |             |    Power BI Reporting      |
      |  - RFM Segmentation        |             |  - Star Schema Model       |
      |  - Customer Lifetime Value |             |  - 15+ DAX Measures        |
      |  - Monthly Retention Cohort|             |  - Curated Datasets        |
      +----------------------------+             +----------------------------+
```

---

## Key Features & Highlights

1. **Realistic Multi-Table Domain Datasets**:
   - 6 core entities: `customers`, `products`, `orders`, `order_items`, `payments`, `returns`.
   - Generates both baseline historical batches (`Batch 1`) and delta batches (`Batch 2`).
2. **Kimball Star Schema Data Warehouse**:
   - Central Grain: Line-item level sales facts (`fact_sales`) and item return facts (`fact_returns`).
   - Dimensions: `dim_customer`, `dim_product`, `dim_date`, `dim_payment_method`, `dim_order_status`.
3. **Slowly Changing Dimensions (SCD Type 2)**:
   - Tracks historical modifications to customer profiles (street, city, state, postal code, phone).
   - Manages `valid_from`, `valid_to`, `is_current`, and sequential `version` numbers.
   - **Point-in-Time Fact Attribution**: Fact sales records dynamically link to the surrogate key valid at the exact time the purchase was made.
4. **Incremental Loading Engine**:
   - High-watermark timestamp tracking stored in `etl_watermark`.
   - Idempotent execution preventing duplicate inserts on pipeline retries.
   - In-place order status updates (e.g., `PENDING` -> `DELIVERED`).
5. **Automated Data Quality & Audit Framework**:
   - 20 automated assertion checks covering completeness, uniqueness, referential integrity, domain constraint validation, and financial reconciliation (`net_revenue = gross - discount`).
   - Automated JSON audit reports output to `data/quality_reports/`.
6. **Dual Database Architecture (PostgreSQL + Local SQLite Fallback)**:
   - Configured out-of-the-box for PostgreSQL.
   - If PostgreSQL is offline, seamlessly and automatically executes on a local SQLite warehouse (`data/warehouse/ecommerce_dw.db`), ensuring 100% executable operation on any Windows/Linux machine without external prerequisites.
7. **Apache Airflow Orchestration**:
   - Standard 2.x DAG (`dags/ecommerce_etl_dag.py`) with task dependencies, retries, and modular operators.
   - Includes a standalone Windows Airflow execution harness (`airflow_runner.py`) simulating exact Airflow execution natively without Docker/WSL.
   - Includes full `docker-compose.yml` for containerized PostgreSQL + Airflow deployments.
8. **Power BI Semantic Layer**:
   - Curated exports in `data/power_bi_export/`.
   - Complete DAX measures library (`power_bi/dax_measures.txt`).
   - Power BI data model diagram and dashboard design blueprints (`power_bi/README_POWER_BI.md`).
9. **Advanced SQL Analytics**:
   - 8 enterprise queries: RFM Segmentation, Customer Lifetime Value (CLV), MoM Growth, Category Margins, Return Diagnostics, Monthly Retention Cohorts, Payment Channel Performance, and SCD2 Historical Attribution.

---

## Star Schema Dimensional Model

```
           +-----------------------+
           |       dim_date        |
           +-----------------------+
           | date_key (PK)         |
           | full_date             |
           | day_of_week           |
           | month_num / name      |
           | quarter / year        |
           | fiscal_quarter        |
           +-----------+-----------+
                       |
                       | 1:N
                       v
+-------------------+  |  +--------------------+
|   dim_customer    |  |  |    dim_product     |
|   (SCD Type 2)    |  |  |    (SCD Type 1)    |
+-------------------+  |  +--------------------+
| dim_customer_key  |  |  | dim_product_key    |
| customer_id (NK)  |  |  | product_id (NK)    |
| full_name         |  |  | product_name       |
| street, city      |  |  | category / subcat  |
| state, country    |  |  | cost_price         |
| valid_from        |  |  | retail_price       |
| valid_to          |  |  | margin_amount / %  |
| is_current        |  |  +---------+----------+
| version           |  |            |
+---------+---------+  |            |
          |            |            |
      1:N |        1:N |        1:N |
          +---------\  |  /---------+
                     v v v
           +-----------------------+
           |      fact_sales       |
           +-----------------------+
           | sales_key (PK)        |
           | order_id / item_id    |
           | dim_customer_key (FK) |
           | dim_product_key  (FK) |
           | dim_order_date_key(FK)|
           | dim_payment_key  (FK) |
           | dim_status_key   (FK) |
           | quantity              |
           | unit_price            |
           | discount_amount       |
           | gross_amount          |
           | net_revenue           |
           | cost_amount           |
           | profit                |
           | tax / shipping fee    |
           +-----------+-----------+
                       ^
                       | 1:N
        +--------------+--------------+
        |                             |
+-------+--------------+    +---------+------------+
|  dim_payment_method  |    |   dim_order_status   |
+----------------------+    +----------------------+
| dim_payment_key (PK) |    | dim_status_key (PK)  |
| payment_method       |    | order_status         |
| payment_channel      |    | is_fulfilled         |
+----------------------+    +----------------------+
```

---

## SCD Type 2 Implementation Explained

In retail and e-commerce, customer demographics (such as shipping address or city) evolve. If a customer lived in Chicago in Q1 and moved to Seattle in Q3, sales made in Q1 should accurately reflect Chicago for regional reporting, while Q3 sales reflect Seattle.

### Mechanism
- Tracked Attributes: `street`, `city`, `state`, `postal_code`, `phone`.
- When an update occurs:
  1. The existing record is closed: `is_current = 0`, `valid_to = record.updated_at`.
  2. A new record is inserted: `version = version + 1`, `is_current = 1`, `valid_from = record.updated_at`, `valid_to = '9999-12-31 23:59:59'`, with a new surrogate key `dim_customer_key`.
- Fact Assignment:
  ```sql
  SELECT dim_customer_key
  FROM dim_customer
  WHERE customer_id = :order_customer_id
    AND valid_from <= :order_timestamp
    AND valid_to >= :order_timestamp;
  ```

### Live Proof Output from Data Warehouse (Query 8)
```
customer_id  customer_version customer_city_version customer_state_version  valid_from           valid_to             is_current  orders_in_version  revenue_attributed
CUST_0006    1                East Carloston        Michigan                2025-01-25 03:38:21  2025-07-14 00:00:00  0           3                  $319.08
CUST_0006    2                North Christopherfort Arizona                 2025-07-14 00:00:00  9999-12-31 23:59:59  1           2                  $214.95
```

---

## Project Structure

```
E-commerce Pipeline/
├── dags/
│   └── ecommerce_etl_dag.py        # Apache Airflow 2.x ETL DAG
├── data/
│   ├── raw/
│   │   ├── batch_1_initial/         # Initial baseline CSVs (Customers, Products, Orders, etc.)
│   │   └── batch_2_incremental/     # Delta CSVs (Address updates, new orders, status updates)
│   ├── processed/                   # Cleaned staging parquet files
│   ├── warehouse/                   # Local SQLite warehouse (ecommerce_dw.db)
│   ├── power_bi_export/             # Curated CSV files for Power BI ingestion
│   └── quality_reports/             # JSON audit logs of automated quality assertions
├── src/
│   ├── __init__.py
│   ├── config.py                    # Environment, directories, engine caching
│   ├── generator.py                 # Realistic sample synthetic data generator
│   ├── ingest.py                    # Schema-validated raw CSV file ingestor
│   ├── clean_validate.py            # Sanitization, type coercion, business checks
│   ├── scd2_handler.py              # SCD Type 2 versioning & point-in-time surrogate lookup
│   ├── transform.py                 # Kimball star schema dimension & fact transformer
│   ├── db_manager.py                # Database connection, transaction, DDL manager
│   ├── incremental_loader.py        # Watermark-driven delta loader
│   ├── quality_checks.py            # Automated data quality assertion framework
│   └── powerbi_export.py            # Power BI export generator
├── sql/
│   ├── ddl_postgres.sql             # PostgreSQL star schema DDL with indexes
│   ├── ddl_sqlite.sql               # SQLite star schema DDL
│   ├── views.sql                    # Semantic analytical reporting views
│   └── analytical_queries.sql       # 8 Advanced business intelligence SQL queries
├── tests/
│   ├── test_cleaning.py             # Data cleansing & validation unit tests
│   ├── test_scd2.py                 # SCD Type 2 versioning & timeline unit tests
│   ├── test_transform.py            # Dimensions & margin calculation unit tests
│   └── test_pipeline_integration.py # Full end-to-end pipeline integration tests
├── power_bi/
│   ├── README_POWER_BI.md           # Step-by-step Power BI Desktop setup guide
│   ├── dax_measures.txt             # 15+ ready-to-use DAX measures
│   └── data_model_schema.json       # Formal star schema relationship model
├── airflow_runner.py                # Standalone Airflow DAG local execution harness for Windows
├── docker-compose.yml               # Containerized PostgreSQL 15 + Apache Airflow stack
├── requirements.txt                 # Python dependencies
├── run_pipeline.py                  # Master CLI pipeline runner
├── .env.example                     # Environment template
└── README.md
```

---

## Getting Started

### 1. Prerequisites
- **Python**: 3.10+ (tested on Python 3.13)
- Optional: PostgreSQL 14+ or Docker (if running with native PostgreSQL)

### 2. Installation
```powershell
# Clone the repository
git clone https://github.com/your-username/ecommerce-data-pipeline.git
cd ecommerce-data-pipeline

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Complete End-to-End Pipeline
Run both Batch 1 (Initial) and Batch 2 (Incremental with SCD2), execute quality audits, export Power BI datasets, and print analytical queries:
```powershell
python run_pipeline.py --batch full
```

### 4. Run Apache Airflow DAG Locally (Windows Native)
You do not need Docker or WSL to validate and run the Airflow DAG:
```powershell
# Run Initial Batch via Airflow Harness
python airflow_runner.py initial

# Run Incremental Batch via Airflow Harness
python airflow_runner.py incremental
```

### 5. Run the Pytest Test Suite
```powershell
python -m pytest -v
```
Output:
```
tests/test_cleaning.py::test_clean_customers PASSED                      [ 12%]
tests/test_cleaning.py::test_clean_products_margin_anomaly PASSED        [ 25%]
tests/test_cleaning.py::test_clean_order_items_calculation PASSED        [ 37%]
tests/test_pipeline_integration.py::test_full_pipeline_lifecycle PASSED  [ 50%]
tests/test_scd2.py::test_scd2_initial_insert PASSED                      [ 62%]
tests/test_scd2.py::test_scd2_address_update_and_pit_lookup PASSED       [ 75%]
tests/test_transform.py::test_date_dimension_generation PASSED           [ 87%]
tests/test_transform.py::test_product_dimension_margins PASSED           [100%]
============================== 8 passed in ~50s ===============================
```

### 6. Running with Docker Compose (PostgreSQL + Airflow)
If running in Docker on Linux/Mac/WSL:
```bash
docker compose up -d
```
- Airflow Web UI: `http://localhost:8080` (Credentials: `admin` / `admin`)
- PostgreSQL Server: `localhost:5432` (`ecommerce_dw`)

---

## SQL Analytical Queries Included

The file [`sql/analytical_queries.sql`](file:///c:/Users/Khushi%20Agarwal/Desktop/E-commerce%20Pipeline/sql/analytical_queries.sql) contains 8 production-grade queries:

1. **Customer Lifetime Value (CLV) Deciles**: Identifies top-spending customers using `NTILE(10)`.
2. **RFM Segmentation**: Categorizes customers into *Champions*, *Loyalists*, *At-Risk*, and *Hibernating* based on Recency, Frequency, and Monetary scores.
3. **MoM Growth & Cumulative Revenue**: Computes month-over-month growth rate and running cumulative annual revenue using window functions (`LAG` and `SUM() OVER`).
4. **Category Profitability & Discount Drag**: Calculates realized profit margins and the revenue impact of discounts across product lines.
5. **Return Rate Diagnostics**: Detects products with the highest return rate percentage and refund costs.
6. **Monthly Cohort Retention**: Analyzes repeat purchase retention rates across monthly customer acquisition cohorts.
7. **Payment Method Analysis**: Breakdown of volume share, average order value, and method reliability.
8. **SCD Type 2 Historical Audit**: Proves that orders placed prior to customer address updates maintain historical attribution, while post-update orders link to version 2.

---

## Power BI Integration

The pipeline exports a fully modeled star schema directly into `data/power_bi_export/`:
1. In Power BI Desktop, load the CSV files from `data/power_bi_export/`.
2. Follow the model relationships documented in [`power_bi/README_POWER_BI.md`](file:///c:/Users/Khushi%20Agarwal/Desktop/E-commerce%20Pipeline/power_bi/README_POWER_BI.md).
3. Copy the DAX measures from [`power_bi/dax_measures.txt`](file:///c:/Users/Khushi%20Agarwal/Desktop/E-commerce%20Pipeline/power_bi/dax_measures.txt).

---

## Resume Highlights (Bullet Points)

- **Engineered an End-to-End E-Commerce Data Pipeline** in Python, PostgreSQL, and Apache Airflow, processing multi-source transactions across customers, orders, payments, and returns into an analytical Kimball Star Schema.
- **Implemented Slowly Changing Dimensions (SCD Type 2)** for customer profile history, ensuring 100% accurate point-in-time fact revenue attribution using surrogate key timeline mapping.
- **Architected an Incremental Watermark Loading Engine** supporting delta detection, idempotent reprocessing, and transaction-safe fact status updates.
- **Built an Automated Data Quality Framework** executing 20 pre- and post-load assertions across schema completeness, foreign key referential integrity, and financial reconciliations.
- **Developed a Power BI Semantic Layer** featuring 15+ DAX financial and cohort retention measures backed by semantic SQL views and optimized dimensional tables.

---

## License
MIT License. Free to use, adapt, and showcase for educational and professional portfolios.
