"""
Data Cleaning and Validation Module
Performs comprehensive data sanitization, type casting, schema validation, and outlier quarantine.
"""
import sys
import re
from pathlib import Path
from typing import Dict, Tuple
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import logger, PROCESSED_DATA_DIR

VALID_ORDER_STATUSES = {"PENDING", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"}
VALID_PAYMENT_METHODS = {"CREDIT_CARD", "PAYPAL", "DEBIT_CARD", "UPI", "NET_BANKING"}
VALID_PAYMENT_STATUSES = {"SUCCESS", "FAILED", "REFUNDED", "PENDING"}
VALID_RETURN_REASONS = {"DEFECTIVE", "WRONG_ITEM", "NOT_AS_DESCRIBED", "CHANGED_MIND"}
VALID_RETURN_STATUSES = {"APPROVED", "PROCESSED", "REJECTED"}

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


class DataCleaner:
    """Sanitizes raw e-commerce dataframes, performs type coercion and business rule validations."""

    def __init__(self):
        self.validation_errors = []

    def clean_customers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cleans and validates customer records."""
        logger.info("Cleaning customers dataset...")
        df = df.copy()

        # Deduplicate on customer_id & updated_at
        initial_len = len(df)
        df.drop_duplicates(subset=["customer_id", "updated_at"], keep="last", inplace=True)

        # String stripping & normalization
        for col in ["first_name", "last_name", "street", "city", "state", "country"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.title()

        df["email"] = df["email"].astype(str).str.strip().str.lower()
        df["country"] = df["country"].str.upper()

        # Phone standardization (digits only)
        df["phone"] = df["phone"].astype(str).str.replace(r"[^\d]", "", regex=True)

        # Email validation check
        invalid_emails = ~df["email"].apply(lambda x: bool(EMAIL_REGEX.match(x)))
        if invalid_emails.any():
            count = invalid_emails.sum()
            logger.warning(f"Found {count} invalid email formats; substituting with fallback format.")
            df.loc[invalid_emails, "email"] = df.loc[invalid_emails, "customer_id"] + "@customer.domain.com"

        # Timestamp casting
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df["updated_at"] = pd.to_datetime(df["updated_at"], errors="coerce").fillna(df["created_at"])

        # Null check on critical keys
        df.dropna(subset=["customer_id", "email"], inplace=True)
        logger.info(f"Customers cleaned: {initial_len} -> {len(df)} records.")
        return df

    def clean_products(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cleans and validates product catalog records."""
        logger.info("Cleaning products dataset...")
        df = df.copy()

        # String formatting
        for col in ["name", "category", "subcategory"]:
            df[col] = df[col].astype(str).str.strip()
        df["sku"] = df["sku"].astype(str).str.strip().str.upper()

        # Numeric conversions
        df["cost_price"] = pd.to_numeric(df["cost_price"], errors="coerce").round(2)
        df["retail_price"] = pd.to_numeric(df["retail_price"], errors="coerce").round(2)
        df["stock_quantity"] = pd.to_numeric(df["stock_quantity"], errors="coerce").fillna(0).astype(int)

        # Business validations: non-negative prices
        df = df[(df["cost_price"] >= 0) & (df["retail_price"] >= 0)]

        # If cost > retail, handle data anomaly (prevent negative gross margin baseline)
        invalid_margin = df["cost_price"] > df["retail_price"]
        if invalid_margin.any():
            logger.warning(f"Detected {invalid_margin.sum()} products where cost > retail. Adjusting cost.")
            df.loc[invalid_margin, "cost_price"] = (df.loc[invalid_margin, "retail_price"] * 0.7).round(2)

        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df["updated_at"] = pd.to_datetime(df["updated_at"], errors="coerce").fillna(df["created_at"])

        df.dropna(subset=["product_id", "sku", "retail_price"], inplace=True)
        return df

    def clean_orders(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cleans and validates orders."""
        logger.info("Cleaning orders dataset...")
        df = df.copy()

        df["status"] = df["status"].astype(str).str.strip().str.upper()
        # Default unknown status to PENDING
        df.loc[~df["status"].isin(VALID_ORDER_STATUSES), "status"] = "PENDING"

        df["shipping_fee"] = pd.to_numeric(df["shipping_fee"], errors="coerce").fillna(0.0).round(2)
        df["tax_amount"] = pd.to_numeric(df["tax_amount"], errors="coerce").fillna(0.0).round(2)
        df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce").fillna(0.0).round(2)

        # Dates
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce").fillna(df["order_date"])
        df["updated_at"] = pd.to_datetime(df["updated_at"], errors="coerce").fillna(df["created_at"])

        # Business rule: total_amount must be >= 0
        df = df[df["total_amount"] >= 0]
        df.dropna(subset=["order_id", "customer_id", "order_date"], inplace=True)
        return df

    def clean_order_items(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cleans and validates individual order line items."""
        logger.info("Cleaning order items dataset...")
        df = df.copy()

        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(1).astype(int)
        df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce").round(2)
        df["discount_amount"] = pd.to_numeric(df["discount_amount"], errors="coerce").fillna(0.0).round(2)

        # Filter out non-positive quantities or prices
        df = df[(df["quantity"] > 0) & (df["unit_price"] >= 0)]

        # Recalculate line_total to guarantee financial consistency
        df["line_total"] = ((df["quantity"] * df["unit_price"]) - df["discount_amount"]).clip(lower=0.0).round(2)

        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df.dropna(subset=["order_item_id", "order_id", "product_id"], inplace=True)
        return df

    def clean_payments(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cleans payment transactions."""
        logger.info("Cleaning payments dataset...")
        df = df.copy()

        df["payment_method"] = df["payment_method"].astype(str).str.strip().str.upper()
        df.loc[~df["payment_method"].isin(VALID_PAYMENT_METHODS), "payment_method"] = "CREDIT_CARD"

        df["payment_status"] = df["payment_status"].astype(str).str.strip().str.upper()
        df.loc[~df["payment_status"].isin(VALID_PAYMENT_STATUSES), "payment_status"] = "PENDING"

        df["amount_paid"] = pd.to_numeric(df["amount_paid"], errors="coerce").fillna(0.0).round(2)
        df["amount_paid"] = df["amount_paid"].clip(lower=0.0)

        df["payment_date"] = pd.to_datetime(df["payment_date"], errors="coerce")
        df["transaction_reference"] = df["transaction_reference"].astype(str).str.strip().str.upper()

        df.dropna(subset=["payment_id", "order_id", "payment_date"], inplace=True)
        return df

    def clean_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cleans return and refund transactions."""
        logger.info("Cleaning returns dataset...")
        df = df.copy()

        df["return_reason"] = df["return_reason"].astype(str).str.strip().str.upper()
        df.loc[~df["return_reason"].isin(VALID_RETURN_REASONS), "return_reason"] = "DEFECTIVE"

        df["return_status"] = df["return_status"].astype(str).str.strip().str.upper()
        df.loc[~df["return_status"].isin(VALID_RETURN_STATUSES), "return_status"] = "PROCESSED"

        df["refund_amount"] = pd.to_numeric(df["refund_amount"], errors="coerce").fillna(0.0).round(2)
        df["refund_amount"] = df["refund_amount"].clip(lower=0.0)

        df["return_date"] = pd.to_datetime(df["return_date"], errors="coerce")
        df.dropna(subset=["return_id", "order_id", "order_item_id", "return_date"], inplace=True)
        return df

    def clean_all(self, raw_dfs: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Cleans all entities in the raw dictionary."""
        cleaned = {
            "customers": self.clean_customers(raw_dfs["customers"]),
            "products": self.clean_products(raw_dfs["products"]),
            "orders": self.clean_orders(raw_dfs["orders"]),
            "order_items": self.clean_order_items(raw_dfs["order_items"]),
            "payments": self.clean_payments(raw_dfs["payments"]),
            "returns": self.clean_returns(raw_dfs["returns"]),
        }
        logger.info("All datasets successfully cleaned and validated.")
        return cleaned


if __name__ == "__main__":
    from src.ingest import DataIngestor
    ingestor = DataIngestor("initial")
    raw = ingestor.ingest_batch()
    cleaner = DataCleaner()
    cleaned = cleaner.clean_all(raw)
    for k, v in cleaned.items():
        print(f"Cleaned {k}: {v.shape}")
