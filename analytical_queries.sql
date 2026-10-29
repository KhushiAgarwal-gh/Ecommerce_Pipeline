-- ============================================================================
-- E-COMMERCE ADVANCED ANALYTICAL SQL QUERIES
-- High-impact business intelligence queries using Star Schema data warehouse
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Customer Lifetime Value (CLV) & Top Decile Customers
-- Identifies top spending customers, their average order size, and purchase cadence.
-- ----------------------------------------------------------------------------
WITH customer_aggregates AS (
    SELECT
        c.customer_id,
        c.full_name,
        c.email,
        c.city,
        c.state,
        COUNT(DISTINCT f.order_id) AS total_orders,
        SUM(f.quantity) AS total_units_bought,
        ROUND(SUM(f.net_revenue), 2) AS total_clv,
        ROUND(AVG(f.net_revenue), 2) AS avg_item_revenue,
        ROUND(SUM(f.profit), 2) AS total_customer_profit
    FROM fact_sales f
    JOIN dim_customer c ON f.dim_customer_key = c.dim_customer_key
    GROUP BY c.customer_id, c.full_name, c.email, c.city, c.state
)
SELECT
    customer_id,
    full_name,
    city,
    state,
    total_orders,
    total_units_bought,
    total_clv,
    total_customer_profit,
    NTILE(10) OVER (ORDER BY total_clv DESC) AS customer_decile
FROM customer_aggregates
ORDER BY total_clv DESC
LIMIT 20;


-- ----------------------------------------------------------------------------
-- 2. RFM Segmentation (Recency, Frequency, Monetary)
-- Segments customer base into actionable loyalty and retention tiers.
-- ----------------------------------------------------------------------------
WITH rfm_base AS (
    SELECT
        c.customer_id,
        c.full_name,
        -- Approximate days since last purchase based on max available date in warehouse
        ROUND(JULIANDAY((SELECT MAX(order_date) FROM fact_sales)) - JULIANDAY(MAX(f.order_date))) AS recency_days,
        COUNT(DISTINCT f.order_id) AS frequency,
        ROUND(SUM(f.net_revenue), 2) AS monetary
    FROM fact_sales f
    JOIN dim_customer c ON f.dim_customer_key = c.dim_customer_key
    GROUP BY c.customer_id, c.full_name
),
rfm_scores AS (
    SELECT
        customer_id,
        full_name,
        recency_days,
        frequency,
        monetary,
        NTILE(4) OVER (ORDER BY recency_days ASC) AS r_score,     -- Lower recency days = higher score
        NTILE(4) OVER (ORDER BY frequency DESC) AS f_score,       -- Higher frequency = higher score
        NTILE(4) OVER (ORDER BY monetary DESC) AS m_score         -- Higher monetary = higher score
    FROM rfm_base
)
SELECT
    customer_id,
    full_name,
    recency_days,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    CASE
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Champion'
        WHEN f_score >= 3 AND m_score >= 2 THEN 'Loyal Customer'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At-Risk High Value'
        WHEN r_score = 1 AND f_score = 1 THEN 'Hibernating / Lost'
        ELSE 'Potential Loyalist'
    END AS customer_segment
FROM rfm_scores
ORDER BY monetary DESC
LIMIT 25;


-- ----------------------------------------------------------------------------
-- 3. Monthly Revenue, MoM Growth Rate & Cumulative Revenue
-- Measures month-over-month performance trends and running year-to-date trajectory.
-- ----------------------------------------------------------------------------
WITH monthly_metrics AS (
    SELECT
        d.year,
        d.month_num,
        d.month_name,
        COUNT(DISTINCT f.order_id) AS order_volume,
        ROUND(SUM(f.net_revenue), 2) AS monthly_net_revenue,
        ROUND(SUM(f.profit), 2) AS monthly_profit
    FROM fact_sales f
    JOIN dim_date d ON f.dim_order_date_key = d.date_key
    GROUP BY d.year, d.month_num, d.month_name
)
SELECT
    year,
    month_num,
    month_name,
    order_volume,
    monthly_net_revenue,
    monthly_profit,
    ROUND(LAG(monthly_net_revenue, 1) OVER (ORDER BY year, month_num), 2) AS prev_month_revenue,
    ROUND(
        ((monthly_net_revenue - LAG(monthly_net_revenue, 1) OVER (ORDER BY year, month_num)) /
        NULLIF(LAG(monthly_net_revenue, 1) OVER (ORDER BY year, month_num), 0)) * 100, 2
    ) AS mom_growth_pct,
    ROUND(SUM(monthly_net_revenue) OVER (ORDER BY year, month_num ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS cumulative_revenue
FROM monthly_metrics
ORDER BY year, month_num;


-- ----------------------------------------------------------------------------
-- 4. Category & Subcategory Profitability Analysis
-- Highlights margin contribution and discount erosion across product lines.
-- ----------------------------------------------------------------------------
SELECT
    p.category,
    p.subcategory,
    COUNT(DISTINCT f.order_id) AS orders_count,
    SUM(f.quantity) AS total_units_sold,
    ROUND(SUM(f.gross_amount), 2) AS total_gross_sales,
    ROUND(SUM(f.discount_amount), 2) AS total_discounts_given,
    ROUND(SUM(f.net_revenue), 2) AS total_net_revenue,
    ROUND(SUM(f.profit), 2) AS total_profit,
    ROUND((SUM(f.profit) / NULLIF(SUM(f.net_revenue), 0)) * 100, 2) AS profit_margin_pct,
    ROUND((SUM(f.discount_amount) / NULLIF(SUM(f.gross_amount), 0)) * 100, 2) AS discount_rate_pct
FROM fact_sales f
JOIN dim_product p ON f.dim_product_key = p.dim_product_key
GROUP BY p.category, p.subcategory
ORDER BY total_net_revenue DESC;


-- ----------------------------------------------------------------------------
-- 5. Product Return Rate & Root Cause Diagnostics
-- Identifies products with abnormally high return volumes and financial refund drag.
-- ----------------------------------------------------------------------------
WITH sales_by_prod AS (
    SELECT
        dim_product_key,
        SUM(quantity) AS units_sold,
        ROUND(SUM(net_revenue), 2) AS total_sales_rev
    FROM fact_sales
    GROUP BY dim_product_key
),
returns_by_prod AS (
    SELECT
        dim_product_key,
        COUNT(return_id) AS total_returns,
        ROUND(SUM(refund_amount), 2) AS total_refunds
    FROM fact_returns
    GROUP BY dim_product_key
)
SELECT
    p.category,
    p.product_name,
    p.retail_price,
    COALESCE(s.units_sold, 0) AS units_sold,
    COALESCE(r.total_returns, 0) AS total_returns,
    ROUND((CAST(COALESCE(r.total_returns, 0) AS REAL) / NULLIF(s.units_sold, 0)) * 100, 2) AS return_rate_pct,
    COALESCE(r.total_refunds, 0.0) AS total_refunded_amount
FROM dim_product p
JOIN sales_by_prod s ON p.dim_product_key = s.dim_product_key
LEFT JOIN returns_by_prod r ON p.dim_product_key = r.dim_product_key
WHERE s.units_sold > 0
ORDER BY return_rate_pct DESC
LIMIT 15;


-- ----------------------------------------------------------------------------
-- 6. Monthly Cohort Retention Analysis
-- Tracks repeat purchasing behaviour grouped by customer first-purchase cohort.
-- ----------------------------------------------------------------------------
WITH customer_first_order AS (
    SELECT
        c.customer_id,
        MIN(SUBSTR(f.order_date, 1, 7)) AS cohort_month
    FROM fact_sales f
    JOIN dim_customer c ON f.dim_customer_key = c.dim_customer_key
    GROUP BY c.customer_id
),
customer_orders AS (
    SELECT
        c.customer_id,
        SUBSTR(f.order_date, 1, 7) AS order_month
    FROM fact_sales f
    JOIN dim_customer c ON f.dim_customer_key = c.dim_customer_key
    GROUP BY c.customer_id, SUBSTR(f.order_date, 1, 7)
)
SELECT
    cfo.cohort_month,
    co.order_month,
    COUNT(DISTINCT co.customer_id) AS active_retained_customers
FROM customer_first_order cfo
JOIN customer_orders co ON cfo.customer_id = co.customer_id
GROUP BY cfo.cohort_month, co.order_month
ORDER BY cfo.cohort_month, co.order_month;


-- ----------------------------------------------------------------------------
-- 7. Payment Method Volume & Channel Breakdown
-- Evaluates transaction distribution and payment method performance.
-- ----------------------------------------------------------------------------
SELECT
    pm.payment_method,
    pm.payment_channel,
    COUNT(DISTINCT f.order_id) AS total_orders_processed,
    ROUND(SUM(f.net_revenue), 2) AS total_volume_processed,
    ROUND(AVG(f.net_revenue), 2) AS avg_transaction_size,
    ROUND(
        (SUM(f.net_revenue) / (SELECT SUM(net_revenue) FROM fact_sales)) * 100, 2
    ) AS volume_share_percentage
FROM fact_sales f
JOIN dim_payment_method pm ON f.dim_payment_key = pm.dim_payment_key
GROUP BY pm.payment_method, pm.payment_channel
ORDER BY total_volume_processed DESC;


-- ----------------------------------------------------------------------------
-- 8. SCD Type 2 Audit Query (Demonstrating Historical Lineage)
-- Verifies that historical orders retain the historical customer address,
-- while subsequent orders after address modification link to version 2!
-- ----------------------------------------------------------------------------
SELECT
    c.customer_id,
    c.version AS customer_version,
    c.city AS customer_city_version,
    c.state AS customer_state_version,
    c.valid_from,
    c.valid_to,
    c.is_current,
    COUNT(f.sales_key) AS orders_placed_in_this_version,
    ROUND(SUM(f.net_revenue), 2) AS revenue_attributed_to_this_version
FROM dim_customer c
LEFT JOIN fact_sales f ON c.dim_customer_key = f.dim_customer_key
WHERE c.customer_id IN (
    SELECT customer_id FROM dim_customer GROUP BY customer_id HAVING COUNT(*) > 1
)
GROUP BY c.customer_id, c.version, c.city, c.state, c.valid_from, c.valid_to, c.is_current
ORDER BY c.customer_id, c.version;
