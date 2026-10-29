-- ============================================================================
-- E-COMMERCE DATA WAREHOUSE DDL (SQLite Dialect)
-- Star Schema Dimensional Model for Analytics & Reporting
-- ============================================================================

-- 1. Date Dimension
CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date TEXT NOT NULL UNIQUE,
    day_of_week INTEGER NOT NULL,
    day_name TEXT NOT NULL,
    day_of_month INTEGER NOT NULL,
    day_of_year INTEGER NOT NULL,
    week_of_year INTEGER NOT NULL,
    month_num INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    quarter INTEGER NOT NULL,
    year INTEGER NOT NULL,
    is_weekend INTEGER NOT NULL,
    fiscal_quarter TEXT NOT NULL
);

-- 2. Customer Dimension (SCD Type 2)
CREATE TABLE IF NOT EXISTS dim_customer (
    dim_customer_key INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    street TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    country TEXT,
    valid_from TEXT NOT NULL,
    valid_to TEXT NOT NULL DEFAULT '9999-12-31 23:59:59',
    is_current INTEGER NOT NULL DEFAULT 1,
    version INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_dim_cust_id_current ON dim_customer(customer_id, is_current);
CREATE INDEX IF NOT EXISTS idx_dim_cust_timeline ON dim_customer(customer_id, valid_from, valid_to);

-- 3. Product Dimension (SCD Type 1)
CREATE TABLE IF NOT EXISTS dim_product (
    dim_product_key INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL UNIQUE,
    sku TEXT NOT NULL,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    cost_price REAL NOT NULL,
    retail_price REAL NOT NULL,
    margin_amount REAL NOT NULL,
    margin_percentage REAL NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT,
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_dim_prod_cat ON dim_product(category, subcategory);

-- 4. Payment Method Dimension
CREATE TABLE IF NOT EXISTS dim_payment_method (
    dim_payment_key INTEGER PRIMARY KEY,
    payment_method TEXT NOT NULL UNIQUE,
    payment_channel TEXT NOT NULL
);

-- 5. Order Status Dimension
CREATE TABLE IF NOT EXISTS dim_order_status (
    dim_status_key INTEGER PRIMARY KEY,
    order_status TEXT NOT NULL UNIQUE,
    is_fulfilled INTEGER NOT NULL,
    is_cancelled INTEGER NOT NULL
);

-- 6. Fact Sales
CREATE TABLE IF NOT EXISTS fact_sales (
    sales_key INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    order_item_id TEXT NOT NULL UNIQUE,
    dim_customer_key INTEGER NOT NULL,
    dim_product_key INTEGER NOT NULL,
    dim_order_date_key INTEGER NOT NULL,
    dim_payment_key INTEGER NOT NULL,
    dim_status_key INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    discount_amount REAL NOT NULL,
    gross_amount REAL NOT NULL,
    net_revenue REAL NOT NULL,
    cost_amount REAL NOT NULL,
    profit REAL NOT NULL,
    tax_amount REAL NOT NULL,
    shipping_fee REAL NOT NULL,
    order_date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(dim_customer_key) REFERENCES dim_customer(dim_customer_key),
    FOREIGN KEY(dim_product_key) REFERENCES dim_product(dim_product_key),
    FOREIGN KEY(dim_order_date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY(dim_payment_key) REFERENCES dim_payment_method(dim_payment_key),
    FOREIGN KEY(dim_status_key) REFERENCES dim_order_status(dim_status_key)
);

CREATE INDEX IF NOT EXISTS idx_fact_sales_order ON fact_sales(order_id);
CREATE INDEX IF NOT EXISTS idx_fact_sales_date ON fact_sales(dim_order_date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_cust ON fact_sales(dim_customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_prod ON fact_sales(dim_product_key);

-- 7. Fact Returns
CREATE TABLE IF NOT EXISTS fact_returns (
    return_key INTEGER PRIMARY KEY AUTOINCREMENT,
    return_id TEXT NOT NULL UNIQUE,
    order_id TEXT NOT NULL,
    order_item_id TEXT NOT NULL,
    dim_customer_key INTEGER NOT NULL,
    dim_product_key INTEGER NOT NULL,
    dim_return_date_key INTEGER NOT NULL,
    return_reason TEXT NOT NULL,
    return_status TEXT NOT NULL,
    refund_amount REAL NOT NULL,
    quantity_returned INTEGER NOT NULL DEFAULT 1,
    return_date TEXT NOT NULL,
    FOREIGN KEY(dim_customer_key) REFERENCES dim_customer(dim_customer_key),
    FOREIGN KEY(dim_product_key) REFERENCES dim_product(dim_product_key),
    FOREIGN KEY(dim_return_date_key) REFERENCES dim_date(date_key)
);

CREATE INDEX IF NOT EXISTS idx_fact_ret_date ON fact_returns(dim_return_date_key);
CREATE INDEX IF NOT EXISTS idx_fact_ret_item ON fact_returns(order_item_id);

-- 8. ETL Watermark Tracking Table
CREATE TABLE IF NOT EXISTS etl_watermark (
    table_name TEXT PRIMARY KEY,
    last_processed_timestamp TEXT NOT NULL,
    records_processed INTEGER DEFAULT 0,
    batch_id TEXT,
    last_run_at TEXT NOT NULL
);
