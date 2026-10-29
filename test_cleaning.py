"""
Unit Tests for Data Cleaning & Validation Module
"""
import pytest
import pandas as pd
from datetime import datetime

from src.clean_validate import DataCleaner


@pytest.fixture
def cleaner():
    return DataCleaner()


def test_clean_customers(cleaner):
    raw_data = pd.DataFrame([{
        "customer_id": "CUST_9999",
        "first_name": "  alice ",
        "last_name": " smith ",
        "email": "  ALICE.SMITH@EXAMPLE.COM  ",
        "phone": "+1 (555) 123-4567",
        "street": "123 Main St",
        "city": "new york",
        "state": "ny",
        "postal_code": "10001",
        "country": "usa",
        "created_at": "2025-01-01 10:00:00",
        "updated_at": "2025-01-01 10:00:00"
    }])

    cleaned = cleaner.clean_customers(raw_data)
    assert len(cleaned) == 1
    row = cleaned.iloc[0]
    assert row["first_name"] == "Alice"
    assert row["last_name"] == "Smith"
    assert row["email"] == "alice.smith@example.com"
    assert row["phone"] == "15551234567"
    assert row["country"] == "USA"


def test_clean_products_margin_anomaly(cleaner):
    # Test where cost price > retail price
    raw_prods = pd.DataFrame([{
        "product_id": "PROD_999",
        "sku": "sku-abc-001",
        "name": " Overpriced Gadget ",
        "category": "Electronics",
        "subcategory": "Gadgets",
        "cost_price": "200.00",
        "retail_price": "100.00",
        "stock_quantity": "50",
        "supplier_id": "SUPP_01",
        "created_at": "2025-01-01 00:00:00",
        "updated_at": "2025-01-01 00:00:00"
    }])

    cleaned = cleaner.clean_products(raw_prods)
    assert len(cleaned) == 1
    row = cleaned.iloc[0]
    assert row["sku"] == "SKU-ABC-001"
    assert row["retail_price"] == 100.00
    # Cost should be adjusted to 70% of retail
    assert row["cost_price"] == 70.00


def test_clean_order_items_calculation(cleaner):
    raw_items = pd.DataFrame([{
        "order_item_id": "ITEM_999",
        "order_id": "ORD_999",
        "product_id": "PROD_001",
        "quantity": "3",
        "unit_price": "50.00",
        "discount_amount": "10.00",
        "line_total": "0.00",  # intentionally bad input to test recalculation
        "created_at": "2025-01-01 12:00:00"
    }])

    cleaned = cleaner.clean_order_items(raw_items)
    assert len(cleaned) == 1
    row = cleaned.iloc[0]
    # line_total = (3 * 50) - 10 = 140.00
    assert row["line_total"] == 140.00
