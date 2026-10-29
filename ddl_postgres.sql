-- ============================================================================
-- E-COMMERCE DATA WAREHOUSE DDL (PostgreSQL Dialect)
-- Star Schema Dimensional Model for Analytics & Reporting
-- ============================================================================

-- 1. Date Dimension (Role-playing dimension)
CREATE TABLE IF NOT EXISTS dim_date (
    date_key INT PRIMARY KEY,                       -- e.g. 20250115
    full_date DATE NOT NULL UNIQUE,
    day_of_week INT NOT NULL,                       -- 1 (Monday) to 7 (Sunday)
    day_name VARCHAR(15) NOT NULL,
    day_of_month INT NOT NULL,
    day_of_year INT NOT NULL,
    week_of_year INT NOT NULL,
    month_num INT NOT NULL,
    month_name VARCHAR(15) NOT NULL,
    quarter INT NOT NULL,
    year INT NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    fiscal_quarter VARCHAR(10) NOT NULL
);

-- 2. Customer Dimension (SCD Type 2: Tracks historical profile and address changes)
CREATE TABLE IF NOT EXISTS dim_customer (
    dim_customer_key SERIAL PRIMARY KEY,             -- Surrogate Key
    customer_id VARCHAR(50) NOT NULL,                -- Natural / Business Key
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    street VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(50),
    country VARCHAR(50),
    valid_from TIMESTAMP NOT NULL,                   -- SCD Type 2 start timestamp
    valid_to TIMESTAMP NOT NULL DEFAULT '9999-12-31 23:59:59', -- SCD Type 2 end timestamp
    is_current BOOLEAN NOT NULL DEFAULT TRUE,        -- SCD Type 2 active flag
    version INT NOT NULL DEFAULT 1                   -- Version counter
);

CREATE INDEX IF NOT EXISTS idx_dim_cust_id_current ON dim_customer(customer_id, is_current);
CREATE INDEX IF NOT EXISTS idx_dim_cust_timeline ON dim_customer(customer_id, valid_from, valid_to);

-- 3. Product Dimension (SCD Type 1)
CREATE TABLE IF NOT EXISTS dim_product (
    dim_product_key SERIAL PRIMARY KEY,              -- Surrogate Key
    product_id VARCHAR(50) NOT NULL UNIQUE,          -- Natural Key
    sku VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100) NOT NULL,
    cost_price DECIMAL(10,2) NOT NULL,
    retail_price DECIMAL(10,2) NOT NULL,
    margin_amount DECIMAL(10,2) NOT NULL,
    margin_percentage DECIMAL(5,2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_prod_cat ON dim_product(category, subcategory);

-- 4. Payment Method Dimension
CREATE TABLE IF NOT EXISTS dim_payment_method (
    dim_payment_key INT PRIMARY KEY,
    payment_method VARCHAR(50) NOT NULL UNIQUE,
    payment_channel VARCHAR(50) NOT NULL
);

-- 5. Order Status Dimension
CREATE TABLE IF NOT EXISTS dim_order_status (
    dim_status_key INT PRIMARY KEY,
    order_status VARCHAR(50) NOT NULL UNIQUE,
    is_fulfilled BOOLEAN NOT NULL,
    is_cancelled BOOLEAN NOT NULL
);

-- 6. Fact Sales (Grain: One row per order line item)
CREATE TABLE IF NOT EXISTS fact_sales (
    sales_key SERIAL PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    order_item_id VARCHAR(50) NOT NULL UNIQUE,
    dim_customer_key INT NOT NULL REFERENCES dim_customer(dim_customer_key),
    dim_product_key INT NOT NULL REFERENCES dim_product(dim_product_key),
    dim_order_date_key INT NOT NULL REFERENCES dim_date(date_key),
    dim_payment_key INT NOT NULL REFERENCES dim_payment_method(dim_payment_key),
    dim_status_key INT NOT NULL REFERENCES dim_order_status(dim_status_key),
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    discount_amount DECIMAL(10,2) NOT NULL,
    gross_amount DECIMAL(10,2) NOT NULL,
    net_revenue DECIMAL(10,2) NOT NULL,
    cost_amount DECIMAL(10,2) NOT NULL,
    profit DECIMAL(10,2) NOT NULL,
    tax_amount DECIMAL(10,2) NOT NULL,
    shipping_fee DECIMAL(10,2) NOT NULL,
    order_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fact_sales_order ON fact_sales(order_id);
CREATE INDEX IF NOT EXISTS idx_fact_sales_date ON fact_sales(dim_order_date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_cust ON fact_sales(dim_customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_prod ON fact_sales(dim_product_key);

-- 7. Fact Returns (Grain: One row per returned item)
CREATE TABLE IF NOT EXISTS fact_returns (
    return_key SERIAL PRIMARY KEY,
    return_id VARCHAR(50) NOT NULL UNIQUE,
    order_id VARCHAR(50) NOT NULL,
    order_item_id VARCHAR(50) NOT NULL,
    dim_customer_key INT NOT NULL REFERENCES dim_customer(dim_customer_key),
    dim_product_key INT NOT NULL REFERENCES dim_product(dim_product_key),
    dim_return_date_key INT NOT NULL REFERENCES dim_date(date_key),
    return_reason VARCHAR(100) NOT NULL,
    return_status VARCHAR(50) NOT NULL,
    refund_amount DECIMAL(10,2) NOT NULL,
    quantity_returned INT NOT NULL DEFAULT 1,
    return_date TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fact_ret_date ON fact_returns(dim_return_date_key);
CREATE INDEX IF NOT EXISTS idx_fact_ret_item ON fact_returns(order_item_id);

-- 8. ETL Watermark Tracking Table
CREATE TABLE IF NOT EXISTS etl_watermark (
    table_name VARCHAR(100) PRIMARY KEY,
    last_processed_timestamp TIMESTAMP NOT NULL,
    records_processed BIGINT DEFAULT 0,
    batch_id VARCHAR(50),
    last_run_at TIMESTAMP NOT NULL
);
