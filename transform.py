"""
Data Transformation and Dimensional Modeling Module
Transforms cleaned staging data into star-schema Dimensions and Facts.
"""
import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db_manager import DatabaseManager
from src.scd2_handler import SCD2Handler
from src.config import logger

PAYMENT_METHOD_METADATA = [
    {"dim_payment_key": 1, "payment_method": "CREDIT_CARD", "payment_channel": "Credit Card"},
    {"dim_payment_key": 2, "payment_method": "DEBIT_CARD", "payment_channel": "Debit Card"},
    {"dim_payment_key": 3, "payment_method": "PAYPAL", "payment_channel": "Digital Wallet"},
    {"dim_payment_key": 4, "payment_method": "UPI", "payment_channel": "Instant Bank Transfer"},
    {"dim_payment_key": 5, "payment_method": "NET_BANKING", "payment_channel": "Online Banking"},
]

ORDER_STATUS_METADATA = [
    {"dim_status_key": 1, "order_status": "PENDING", "is_fulfilled": 0, "is_cancelled": 0},
    {"dim_status_key": 2, "order_status": "PROCESSING", "is_fulfilled": 0, "is_cancelled": 0},
    {"dim_status_key": 3, "order_status": "SHIPPED", "is_fulfilled": 0, "is_cancelled": 0},
    {"dim_status_key": 4, "order_status": "DELIVERED", "is_fulfilled": 1, "is_cancelled": 0},
    {"dim_status_key": 5, "order_status": "CANCELLED", "is_fulfilled": 0, "is_cancelled": 1},
    {"dim_status_key": 6, "order_status": "RETURNED", "is_fulfilled": 1, "is_cancelled": 0},
]


class DataTransformer:
    """Transforms staged data into star schema dimension and fact tables."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.scd2 = SCD2Handler(db_manager)

    def load_static_dimensions(self):
        """Loads dim_payment_method and dim_order_status reference dimensions if not already present."""
        logger.info("Verifying static reference dimensions...")
        
        # Payment Method
        if self.db.get_table_count("dim_payment_method") == 0:
            pay_df = pd.DataFrame(PAYMENT_METHOD_METADATA)
            self.db.insert_dataframe("dim_payment_method", pay_df, if_exists="append")

        # Order Status
        if self.db.get_table_count("dim_order_status") == 0:
            status_df = pd.DataFrame(ORDER_STATUS_METADATA)
            self.db.insert_dataframe("dim_order_status", status_df, if_exists="append")

    def load_date_dimension(self, start_date: str = "2024-01-01", end_date: str = "2026-12-31"):
        """Generates and populates the dim_date calendar dimension."""
        if self.db.get_table_count("dim_date") > 0:
            logger.info("dim_date dimension already populated. Skipping generation.")
            return

        logger.info(f"Generating dim_date dimension from {start_date} to {end_date}...")
        cur_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        stop_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        date_records = []
        while cur_date <= stop_date:
            date_key = int(cur_date.strftime("%Y%m%d"))
            quarter = (cur_date.month - 1) // 3 + 1
            is_weekend = 1 if cur_date.weekday() in [5, 6] else 0
            fiscal_quarter = f"FY{str(cur_date.year)[2:]}-Q{quarter}"

            date_records.append({
                "date_key": date_key,
                "full_date": cur_date.strftime("%Y-%m-%d"),
                "day_of_week": cur_date.weekday() + 1,  # 1=Monday, 7=Sunday
                "day_name": cur_date.strftime("%A"),
                "day_of_month": cur_date.day,
                "day_of_year": cur_date.timetuple().tm_yday,
                "week_of_year": cur_date.isocalendar()[1],
                "month_num": cur_date.month,
                "month_name": cur_date.strftime("%B"),
                "quarter": quarter,
                "year": cur_date.year,
                "is_weekend": is_weekend if self.db.dialect == "sqlite" else bool(is_weekend),
                "fiscal_quarter": fiscal_quarter
            })
            cur_date += timedelta(days=1)

        date_df = pd.DataFrame(date_records)
        self.db.insert_dataframe("dim_date", date_df, if_exists="append", chunksize=2000)
        logger.info(f"Populated dim_date with {len(date_df)} calendar records.")

    def load_product_dimension(self, products_df: pd.DataFrame) -> int:
        """
        Loads products into dim_product (SCD Type 1 - updates in place, inserts new).
        Computes margin amount and margin percentage.
        """
        logger.info(f"Transforming and loading {len(products_df)} products into dim_product...")
        existing_df = self.db.query_to_df("SELECT dim_product_key, product_id FROM dim_product")
        existing_map = dict(zip(existing_df["product_id"], existing_df["dim_product_key"])) if not existing_df.empty else {}

        max_key_df = self.db.query_to_df("SELECT COALESCE(MAX(dim_product_key), 0) AS max_k FROM dim_product")
        current_key = int(max_key_df.iloc[0]["max_k"])

        new_products = []
        updated_count = 0

        for _, row in products_df.iterrows():
            prod_id = row["product_id"]
            cost = float(row["cost_price"])
            retail = float(row["retail_price"])
            margin_amt = round(retail - cost, 2)
            margin_pct = round((margin_amt / retail * 100), 2) if retail > 0 else 0.0

            if prod_id in existing_map:
                # SCD Type 1: Update existing product attributes
                key = existing_map[prod_id]
                update_sql = """
                    UPDATE dim_product
                    SET cost_price = :cost,
                        retail_price = :retail,
                        margin_amount = :margin_amt,
                        margin_percentage = :margin_pct,
                        updated_at = :upd
                    WHERE dim_product_key = :k
                """
                self.db.execute(update_sql, {
                    "cost": cost,
                    "retail": retail,
                    "margin_amt": margin_amt,
                    "margin_pct": margin_pct,
                    "upd": str(row.get("updated_at", datetime.now())),
                    "k": key
                })
                updated_count += 1
            else:
                current_key += 1
                new_products.append({
                    "dim_product_key": current_key,
                    "product_id": prod_id,
                    "sku": row["sku"],
                    "product_name": row["name"],
                    "category": row["category"],
                    "subcategory": row["subcategory"],
                    "cost_price": cost,
                    "retail_price": retail,
                    "margin_amount": margin_amt,
                    "margin_percentage": margin_pct,
                    "is_active": 1 if self.db.dialect == "sqlite" else True,
                    "created_at": str(row.get("created_at", datetime.now())),
                    "updated_at": str(row.get("updated_at", datetime.now()))
                })

        if new_products:
            new_df = pd.DataFrame(new_products)
            self.db.insert_dataframe("dim_product", new_df, if_exists="append")

        logger.info(f"dim_product loaded: {len(new_products)} inserted, {updated_count} updated.")
        return len(new_products) + updated_count

    def build_fact_sales(self, cleaned_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Transforms cleaned orders, order_items, payments, and dimensions into fact_sales.
        Applies point-in-time SCD2 surrogate key lookup for dim_customer.
        """
        orders_df = cleaned_data["orders"].copy()
        items_df = cleaned_data["order_items"].copy()
        payments_df = cleaned_data["payments"].copy()

        logger.info(f"Building fact_sales from {len(items_df)} order items and {len(orders_df)} orders...")

        # 1. Product mapping
        prod_dim = self.db.query_to_df("SELECT dim_product_key, product_id, cost_price FROM dim_product")
        prod_map = dict(zip(prod_dim["product_id"], prod_dim["dim_product_key"]))
        prod_cost_map = dict(zip(prod_dim["product_id"], prod_dim["cost_price"]))

        # 2. Payment method & status mappings
        pay_dim = self.db.query_to_df("SELECT dim_payment_key, payment_method FROM dim_payment_method")
        pay_map = dict(zip(pay_dim["payment_method"], pay_dim["dim_payment_key"]))

        status_dim = self.db.query_to_df("SELECT dim_status_key, order_status FROM dim_order_status")
        status_map = dict(zip(status_dim["order_status"], status_dim["dim_status_key"]))

        # 3. Order-level lookup maps
        orders_dict = orders_df.set_index("order_id").to_dict(orient="index")
        
        # Payment lookup by order_id (first successful or latest payment)
        payments_by_order = {}
        for _, pay_row in payments_df.iterrows():
            payments_by_order[pay_row["order_id"]] = pay_row["payment_method"]

        # Cache customer surrogate key lookups to optimize performance
        cust_key_cache = {}

        # Get existing fact sales keys if any
        max_sales_key_df = self.db.query_to_df("SELECT COALESCE(MAX(sales_key), 0) AS max_k FROM fact_sales")
        current_sales_key = int(max_sales_key_df.iloc[0]["max_k"])

        fact_rows = []
        for _, item in items_df.iterrows():
            ord_id = item["order_id"]
            if ord_id not in orders_dict:
                continue

            order = orders_dict[ord_id]
            cust_id = order["customer_id"]
            order_dt_str = str(order["order_date"])

            # Resolve SCD Type 2 point-in-time dim_customer_key
            cache_key = (cust_id, order_dt_str[:10])
            if cache_key not in cust_key_cache:
                cust_key_cache[cache_key] = self.scd2.get_customer_key_as_of(cust_id, order_dt_str)
            cust_key = cust_key_cache[cache_key]
            if not cust_key:
                # If not resolved, skip or fallback to 1
                continue

            prod_id = item["product_id"]
            prod_key = prod_map.get(prod_id)
            if not prod_key:
                continue

            # Date key: YYYYMMDD
            try:
                dt_obj = pd.to_datetime(order["order_date"])
                date_key = int(dt_obj.strftime("%Y%m%d"))
            except Exception:
                date_key = 20250101

            # Payment method key
            pay_method = payments_by_order.get(ord_id, "CREDIT_CARD")
            dim_pay_key = pay_map.get(pay_method, 1)

            # Status key
            ord_status = order["status"]
            dim_status_key = status_map.get(ord_status, 1)

            # Metrics
            qty = int(item["quantity"])
            u_price = float(item["unit_price"])
            disc = float(item["discount_amount"])
            gross = round(qty * u_price, 2)
            net_rev = round(gross - disc, 2)
            prod_cost = float(prod_cost_map.get(prod_id, u_price * 0.6))
            cost_amt = round(qty * prod_cost, 2)
            profit = round(net_rev - cost_amt, 2)

            # Allocation of order shipping & tax per item proportion
            order_tot = float(order.get("total_amount", gross))
            proportion = (net_rev / order_tot) if order_tot > 0 else 0.5
            tax_alloc = round(float(order.get("tax_amount", 0.0)) * proportion, 2)
            ship_alloc = round(float(order.get("shipping_fee", 0.0)) * proportion, 2)

            current_sales_key += 1
            fact_rows.append({
                "sales_key": current_sales_key,
                "order_id": ord_id,
                "order_item_id": item["order_item_id"],
                "dim_customer_key": cust_key,
                "dim_product_key": prod_key,
                "dim_order_date_key": date_key,
                "dim_payment_key": dim_pay_key,
                "dim_status_key": dim_status_key,
                "quantity": qty,
                "unit_price": u_price,
                "discount_amount": disc,
                "gross_amount": gross,
                "net_revenue": net_rev,
                "cost_amount": cost_amt,
                "profit": profit,
                "tax_amount": tax_alloc,
                "shipping_fee": ship_alloc,
                "order_date": order_dt_str,
                "created_at": str(order.get("created_at", order_dt_str)),
                "updated_at": str(order.get("updated_at", order_dt_str))
            })

        fact_sales_df = pd.DataFrame(fact_rows)
        logger.info(f"Built fact_sales: {len(fact_sales_df)} line-item fact records.")
        return fact_sales_df

    def build_fact_returns(self, cleaned_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Transforms cleaned returns into fact_returns linked to dim_customer, dim_product, dim_date.
        """
        returns_df = cleaned_data["returns"].copy()
        items_df = cleaned_data["order_items"].copy().set_index("order_item_id")
        orders_df = cleaned_data["orders"].copy().set_index("order_id")

        logger.info(f"Building fact_returns from {len(returns_df)} return transactions...")

        prod_dim = self.db.query_to_df("SELECT dim_product_key, product_id FROM dim_product")
        prod_map = dict(zip(prod_dim["product_id"], prod_dim["dim_product_key"]))

        max_ret_key_df = self.db.query_to_df("SELECT COALESCE(MAX(return_key), 0) AS max_k FROM fact_returns")
        current_ret_key = int(max_ret_key_df.iloc[0]["max_k"])

        fact_ret_rows = []
        for _, ret in returns_df.iterrows():
            item_id = ret["order_item_id"]
            ord_id = ret["order_id"]
            ret_dt_str = str(ret["return_date"])

            # Resolve customer & product from item and order
            if item_id in items_df.index:
                item_row = items_df.loc[item_id]
                prod_id = item_row["product_id"] if isinstance(item_row, pd.Series) else item_row.iloc[0]["product_id"]
            else:
                continue

            if ord_id in orders_df.index:
                order_row = orders_df.loc[ord_id]
                cust_id = order_row["customer_id"] if isinstance(order_row, pd.Series) else order_row.iloc[0]["customer_id"]
            else:
                continue

            cust_key = self.scd2.get_customer_key_as_of(cust_id, ret_dt_str)
            prod_key = prod_map.get(prod_id)
            if not cust_key or not prod_key:
                continue

            try:
                ret_dt_obj = pd.to_datetime(ret["return_date"])
                date_key = int(ret_dt_obj.strftime("%Y%m%d"))
            except Exception:
                date_key = 20250101

            current_ret_key += 1
            fact_ret_rows.append({
                "return_key": current_ret_key,
                "return_id": ret["return_id"],
                "order_id": ord_id,
                "order_item_id": item_id,
                "dim_customer_key": cust_key,
                "dim_product_key": prod_key,
                "dim_return_date_key": date_key,
                "return_reason": ret["return_reason"],
                "return_status": ret["return_status"],
                "refund_amount": float(ret["refund_amount"]),
                "quantity_returned": 1,
                "return_date": ret_dt_str
            })

        fact_returns_df = pd.DataFrame(fact_ret_rows)
        logger.info(f"Built fact_returns: {len(fact_returns_df)} return records.")
        return fact_returns_df
