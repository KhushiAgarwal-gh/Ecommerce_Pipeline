"""
Power BI Data Layer Exporter
Exports warehouse dimensional models and analytical views into curated files ready for Power BI Desktop.
"""
import sys
from pathlib import Path
from typing import Dict
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db_manager import DatabaseManager
from src.config import POWERBI_EXPORT_DIR, logger


def export_powerbi_data(db_manager: DatabaseManager) -> Dict[str, str]:
    """Exports star schema tables and curated analytical views for Power BI ingestion."""
    logger.info(f"Exporting curated Data Warehouse datasets to {POWERBI_EXPORT_DIR} for Power BI...")
    POWERBI_EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    tables_and_views = [
        "dim_date",
        "dim_customer",
        "dim_product",
        "dim_payment_method",
        "dim_order_status",
        "fact_sales",
        "fact_returns",
        "vw_monthly_sales_kpi",
        "vw_customer_rfm_summary",
        "vw_product_performance",
        "vw_return_analysis",
        "vw_sales_summary_powerbi"
    ]

    exported_files = {}

    for name in tables_and_views:
        try:
            df = db_manager.query_to_df(f"SELECT * FROM {name}")
            export_path = POWERBI_EXPORT_DIR / f"{name}.csv"
            df.to_csv(export_path, index=False, encoding="utf-8")
            exported_files[name] = str(export_path)
            logger.info(f"Exported {name}: {len(df)} rows -> {export_path.name}")
        except Exception as e:
            logger.warning(f"Could not export {name}: {e}")

    logger.info(f"Power BI data export completed ({len(exported_files)} files exported).")
    return exported_files


if __name__ == "__main__":
    db = DatabaseManager()
    export_powerbi_data(db)
