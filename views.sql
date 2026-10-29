-- ============================================================================
-- SEMANTIC ANALYTICAL VIEWS
-- Business Intelligence & Reporting Views for PostgreSQL / SQLite
-- ============================================================================

-- 1. Monthly Executive Sales KPIs
CREATE VIEW IF NOT EXISTS vw_monthly_sales_kpi AS
SELECT
    d.year,
    d.month_num,
    d.month_name,
    COUNT(DISTINCT f.order_id) AS total_orders,
    SUM(f.quantity) AS total_units_sold,
    ROUND(SUM(f.gross_amount), 2) AS total_gross_sales,
    ROUND(SUM(f.discount_amount), 2) AS total_discounts,
    ROUND(SUM(f.net_revenue), 2) AS total_net_revenue,
    ROUND(SUM(f.profit), 2) AS total_profit,
    ROUND((SUM(f.profit) / NULLIF(SUM(f.net_revenue), 0)) * 100, 2) AS profit_margin_pct,
    ROUND(SUM(f.net_revenue) / NULLIF(COUNT(DISTINCT f.order_id), 0), 2) AS average_order_value
FROM fact_sales f
JOIN dim_date d ON f.dim_order_date_key = d.date_key
GROUP BY d.year, d.month_num, d.month_name;

-- 2. Customer RFM (Recency, Frequency, Monetary) Segmentation
CREATE VIEW IF NOT EXISTS vw_customer_rfm_summary AS
SELECT
    c.customer_id,
    c.full_name,
    c.email,
    c.city,
    c.state,
    COUNT(DISTINCT f.order_id) AS total_orders,
    SUM(f.quantity) AS total_items_purchased,
    ROUND(SUM(f.net_revenue), 2) AS monetary_lifetime_spend,
    ROUND(AVG(f.net_revenue), 2) AS avg_item_spend,
    MIN(f.order_date) AS first_purchase_date,
    MAX(f.order_date) AS last_purchase_date
FROM fact_sales f
JOIN dim_customer c ON f.dim_customer_key = c.dim_customer_key
GROUP BY c.customer_id, c.full_name, c.email, c.city, c.state;

-- 3. Product Performance & Margin Analysis
CREATE VIEW IF NOT EXISTS vw_product_performance AS
SELECT
    p.category,
    p.subcategory,
    p.product_name,
    p.retail_price,
    SUM(f.quantity) AS total_units_sold,
    ROUND(SUM(f.net_revenue), 2) AS total_revenue,
    ROUND(SUM(f.profit), 2) AS total_profit,
    ROUND((SUM(f.profit) / NULLIF(SUM(f.net_revenue), 0)) * 100, 2) AS realized_margin_pct
FROM fact_sales f
JOIN dim_product p ON f.dim_product_key = p.dim_product_key
GROUP BY p.category, p.subcategory, p.product_name, p.retail_price;

-- 4. Returns & Return Reasons Diagnostic
CREATE VIEW IF NOT EXISTS vw_return_analysis AS
SELECT
    p.category,
    r.return_reason,
    COUNT(r.return_id) AS return_count,
    ROUND(SUM(r.refund_amount), 2) AS total_refunded
FROM fact_returns r
JOIN dim_product p ON r.dim_product_key = p.dim_product_key
GROUP BY p.category, r.return_reason;

-- 5. Power BI Flattened Analytical View
CREATE VIEW IF NOT EXISTS vw_sales_summary_powerbi AS
SELECT
    f.sales_key,
    f.order_id,
    f.order_item_id,
    f.order_date,
    d.full_date,
    d.year,
    d.quarter,
    d.month_name,
    d.month_num,
    d.day_name,
    d.is_weekend,
    c.customer_id,
    c.full_name AS customer_name,
    c.city AS customer_city,
    c.state AS customer_state,
    c.country AS customer_country,
    c.version AS customer_scd2_version,
    p.product_id,
    p.product_name,
    p.category AS product_category,
    p.subcategory AS product_subcategory,
    pm.payment_method,
    pm.payment_channel,
    os.order_status,
    f.quantity,
    f.unit_price,
    f.discount_amount,
    f.gross_amount,
    f.net_revenue,
    f.cost_amount,
    f.profit,
    f.tax_amount,
    f.shipping_fee
FROM fact_sales f
JOIN dim_date d ON f.dim_order_date_key = d.date_key
JOIN dim_customer c ON f.dim_customer_key = c.dim_customer_key
JOIN dim_product p ON f.dim_product_key = p.dim_product_key
JOIN dim_payment_method pm ON f.dim_payment_key = pm.dim_payment_key
JOIN dim_order_status os ON f.dim_status_key = os.dim_status_key;
