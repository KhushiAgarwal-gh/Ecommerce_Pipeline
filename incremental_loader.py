"""
Incremental Loading Engine
Orchestrates delta loading, watermark management, upserts, and fact updates.
"""
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db_manager import DatabaseManager
from src.scd2_handler import SCD2Handler
from src.transform import DataTransformer
from src.config import logger


class IncrementalLoader:
    """Manages incremental ETL loading into the star-schema warehouse using watermarks."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.scd2 = SCD2Handler(db_manager)
        self.transformer = DataTransformer(db_manager)

    def load_initial_batch(self, cleaned_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Loads Batch 1 into an empty or freshly initialized warehouse."""
        logger.info("=== Starting Initial Batch Load (Batch 1) ===")
        batch_id = "BATCH_1_INITIAL"

        # 1. Static & Date dimensions
        self.transformer.load_static_dimensions()
        self.transformer.load_date_dimension()

        # 2. Customers Dimension (SCD Type 2 Initial Load)
        scd_results = self.scd2.process_customers_scd2(cleaned_data["customers"])

        # 3. Products Dimension (SCD Type 1 Initial Load)
        prod_count = self.transformer.load_product_dimension(cleaned_data["products"])

        # 4. Fact Sales (idempotent check)
        fact_sales = self.transformer.build_fact_sales(cleaned_data)
        existing_items_df = self.db.query_to_df("SELECT order_item_id FROM fact_sales")
        if not existing_items_df.empty:
            existing_items = set(existing_items_df["order_item_id"])
            fact_sales = fact_sales[~fact_sales["order_item_id"].isin(existing_items)]
        sales_count = self.db.insert_dataframe("fact_sales", fact_sales, if_exists="append") if not fact_sales.empty else 0

        # 5. Fact Returns (idempotent check)
        fact_returns = self.transformer.build_fact_returns(cleaned_data)
        existing_rets_df = self.db.query_to_df("SELECT return_id FROM fact_returns")
        if not existing_rets_df.empty:
            existing_rets = set(existing_rets_df["return_id"])
            fact_returns = fact_returns[~fact_returns["return_id"].isin(existing_rets)]
        returns_count = self.db.insert_dataframe("fact_returns", fact_returns, if_exists="append") if not fact_returns.empty else 0

        # 6. Set watermarks
        max_order_ts = str(cleaned_data["orders"]["updated_at"].max())
        max_cust_ts = str(cleaned_data["customers"]["updated_at"].max())
        max_prod_ts = str(cleaned_data["products"]["updated_at"].max())
        max_ret_ts = str(cleaned_data["returns"]["return_date"].max())

        self.db.update_watermark("dim_customer", max_cust_ts, scd_results["new_customers"], batch_id)
        self.db.update_watermark("dim_product", max_prod_ts, prod_count, batch_id)
        self.db.update_watermark("fact_sales", max_order_ts, sales_count, batch_id)
        self.db.update_watermark("fact_returns", max_ret_ts, returns_count, batch_id)

        logger.info("=== Initial Batch Load Completed Successfully ===")
        return {
            "batch_id": batch_id,
            "customers_loaded": scd_results["new_customers"],
            "products_loaded": prod_count,
            "sales_records": sales_count,
            "returns_records": returns_count,
            "watermark_sales": max_order_ts
        }

    def load_incremental_batch(self, cleaned_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Loads Batch 2 incrementally using delta records, watermarks, and SCD2."""
        logger.info("=== Starting Incremental Batch Load (Batch 2) ===")
        batch_id = "BATCH_2_INCREMENTAL"

        sales_watermark = self.db.get_watermark("fact_sales") or "1970-01-01"
        logger.info(f"Existing fact_sales watermark: {sales_watermark}")

        # 1. SCD2 Customers Delta
        cust_delta = cleaned_data["customers"]
        scd_results = self.scd2.process_customers_scd2(cust_delta)

        # 2. SCD1 Products Delta
        prod_delta = cleaned_data["products"]
        prod_count = self.transformer.load_product_dimension(prod_delta)

        # 3. Check for order status updates on existing orders
        orders_df = cleaned_data["orders"]
        existing_order_ids_df = self.db.query_to_df("SELECT DISTINCT order_id FROM fact_sales")
        existing_order_ids = set(existing_order_ids_df["order_id"]) if not existing_order_ids_df.empty else set()

        status_dim = self.db.query_to_df("SELECT dim_status_key, order_status FROM dim_order_status")
        status_map = dict(zip(status_dim["order_status"], status_dim["dim_status_key"]))

        orders_to_update = orders_df[orders_df["order_id"].isin(existing_order_ids)]
        logger.info(f"Found {len(orders_to_update)} existing orders with potential updates...")
        for _, upd_ord in orders_to_update.iterrows():
            new_status = upd_ord["status"]
            new_status_key = status_map.get(new_status, 1)
            upd_ts = str(upd_ord.get("updated_at", datetime.now()))
            self.db.execute(
                """
                UPDATE fact_sales
                SET dim_status_key = :st_key, updated_at = :upd
                WHERE order_id = :oid
                """,
                {"st_key": new_status_key, "upd": upd_ts, "oid": upd_ord["order_id"]}
            )

        # 4. Insert newly placed orders & items
        new_orders = orders_df[~orders_df["order_id"].isin(existing_order_ids)]
        new_order_ids = set(new_orders["order_id"])
        new_items = cleaned_data["order_items"][cleaned_data["order_items"]["order_id"].isin(new_order_ids)]
        
        subset_data = cleaned_data.copy()
        subset_data["orders"] = new_orders
        subset_data["order_items"] = new_items

        new_fact_sales = self.transformer.build_fact_sales(subset_data)
        new_sales_count = 0
        if not new_fact_sales.empty:
            new_sales_count = self.db.insert_dataframe("fact_sales", new_fact_sales, if_exists="append")

        # 5. Incremental returns
        existing_ret_df = self.db.query_to_df("SELECT return_id FROM fact_returns")
        existing_ret_ids = set(existing_ret_df["return_id"]) if not existing_ret_df.empty else set()
        new_returns_clean = cleaned_data["returns"][~cleaned_data["returns"]["return_id"].isin(existing_ret_ids)]
        
        subset_ret_data = cleaned_data.copy()
        subset_ret_data["returns"] = new_returns_clean
        new_fact_returns = self.transformer.build_fact_returns(subset_ret_data)
        new_returns_count = 0
        if not new_fact_returns.empty:
            new_returns_count = self.db.insert_dataframe("fact_returns", new_fact_returns, if_exists="append")

        # 6. Advance watermarks
        new_max_order_ts = str(orders_df["updated_at"].max())
        new_max_cust_ts = str(cust_delta["updated_at"].max())
        new_max_prod_ts = str(prod_delta["updated_at"].max())
        new_max_ret_ts = str(cleaned_data["returns"]["return_date"].max())

        self.db.update_watermark("dim_customer", new_max_cust_ts, scd_results["new_customers"] + scd_results["updated_scd2_versions"], batch_id)
        self.db.update_watermark("dim_product", new_max_prod_ts, prod_count, batch_id)
        self.db.update_watermark("fact_sales", new_max_order_ts, new_sales_count + len(orders_to_update), batch_id)
        self.db.update_watermark("fact_returns", new_max_ret_ts, new_returns_count, batch_id)

        logger.info("=== Incremental Batch Load Completed Successfully ===")
        return {
            "batch_id": batch_id,
            "scd2_new_customers": scd_results["new_customers"],
            "scd2_updated_versions": scd_results["updated_scd2_versions"],
            "orders_updated": len(orders_to_update),
            "new_sales_records_inserted": new_sales_count,
            "new_returns_inserted": new_returns_count,
            "advanced_watermark": new_max_order_ts
        }
