"""
Data Ingestion Module
Loads raw CSV data batches from source storage and performs initial schema/integrity ingestion checks.
"""
import sys
from pathlib import Path
from typing import Dict, Optional
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import RAW_BATCH_1_DIR, RAW_BATCH_2_DIR, logger

EXPECTED_SCHEMAS = {
    "customers": [
        "customer_id", "first_name", "last_name", "email", "phone",
        "street", "city", "state", "postal_code", "country", "created_at", "updated_at"
    ],
    "products": [
        "product_id", "sku", "name", "category", "subcategory",
        "cost_price", "retail_price", "stock_quantity", "supplier_id", "created_at", "updated_at"
    ],
    "orders": [
        "order_id", "customer_id", "order_date", "status",
        "shipping_fee", "tax_amount", "total_amount", "shipping_address", "created_at", "updated_at"
    ],
    "order_items": [
        "order_item_id", "order_id", "product_id", "quantity",
        "unit_price", "discount_amount", "line_total", "created_at"
    ],
    "payments": [
        "payment_id", "order_id", "payment_date", "payment_method",
        "payment_status", "amount_paid", "transaction_reference"
    ],
    "returns": [
        "return_id", "order_id", "order_item_id", "return_date",
        "return_reason", "refund_amount", "return_status"
    ]
}


class DataIngestor:
    """Handles raw data file loading and schema validation during ingestion."""

    def __init__(self, batch_type: str = "initial", custom_path: Optional[Path] = None):
        self.batch_type = batch_type.lower()
        if custom_path:
            self.source_dir = Path(custom_path)
        elif self.batch_type in ["initial", "batch_1"]:
            self.source_dir = RAW_BATCH_1_DIR
        elif self.batch_type in ["incremental", "batch_2"]:
            self.source_dir = RAW_BATCH_2_DIR
        else:
            raise ValueError(f"Unknown batch_type '{batch_type}'. Expected 'initial' or 'incremental'.")

    def _get_file_mapping(self) -> Dict[str, str]:
        """Returns entity to filename mapping depending on batch type."""
        if self.batch_type in ["initial", "batch_1"]:
            return {
                "customers": "customers.csv",
                "products": "products.csv",
                "orders": "orders.csv",
                "order_items": "order_items.csv",
                "payments": "payments.csv",
                "returns": "returns.csv",
            }
        else:
            return {
                "customers": "customers_delta.csv",
                "products": "products_delta.csv",
                "orders": "orders_delta.csv",
                "order_items": "order_items_delta.csv",
                "payments": "payments_delta.csv",
                "returns": "returns_delta.csv",
            }

    def ingest_batch(self) -> Dict[str, pd.DataFrame]:
        """
        Loads all required CSV files for the batch, validates column schemas,
        and returns a dictionary of DataFrames.
        """
        logger.info(f"Starting data ingestion from: {self.source_dir} (Batch: {self.batch_type})")
        file_mapping = self._get_file_mapping()
        raw_dfs = {}

        for entity, filename in file_mapping.items():
            file_path = self.source_dir / filename
            if not file_path.exists():
                raise FileNotFoundError(f"Required ingestion file not found: {file_path}")

            logger.info(f"Ingesting {entity} from {filename}...")
            df = pd.read_csv(file_path, dtype=str)  # Read raw as string to preserve data formats for cleaning

            # Validate expected columns are present
            expected_cols = set(EXPECTED_SCHEMAS[entity])
            actual_cols = set(df.columns)
            missing_cols = expected_cols - actual_cols

            if missing_cols:
                raise ValueError(f"Ingestion schema mismatch in {filename}! Missing columns: {missing_cols}")

            # Keep only expected columns in order
            df = df[EXPECTED_SCHEMAS[entity]]
            raw_dfs[entity] = df
            logger.info(f"Loaded {entity}: {len(df)} rows, {len(df.columns)} columns.")

        logger.info(f"Batch ingestion completed successfully for {len(raw_dfs)} entities.")
        return raw_dfs


if __name__ == "__main__":
    ingestor = DataIngestor("initial")
    dfs = ingestor.ingest_batch()
    for name, df in dfs.items():
        print(f"{name}: {df.shape}")
