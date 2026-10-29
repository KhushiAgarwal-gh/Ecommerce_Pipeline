"""
Unit Tests for Data Transformation and Star Schema Builders
"""
import pytest
import pandas as pd
from sqlalchemy import create_engine

from src.db_manager import DatabaseManager
from src.transform import DataTransformer


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_dw_transform.db"
    engine = create_engine(f"sqlite:///{db_file}")
    db = DatabaseManager(engine=engine, force_sqlite=True)
    db.init_schema(drop_first=True)
    return db


def test_date_dimension_generation(test_db):
    transformer = DataTransformer(test_db)
    transformer.load_date_dimension(start_date="2025-01-01", end_date="2025-01-05")

    df = test_db.query_to_df("SELECT * FROM dim_date ORDER BY date_key")
    assert len(df) == 5
    assert df.iloc[0]["date_key"] == 20250101
    assert df.iloc[0]["fiscal_quarter"] == "FY25-Q1"
    assert df.iloc[0]["month_name"] == "January"


def test_product_dimension_margins(test_db):
    transformer = DataTransformer(test_db)
    prods = pd.DataFrame([{
        "product_id": "PROD_T1",
        "sku": "SKU-T1",
        "name": "Widget Deluxe",
        "category": "Tools",
        "subcategory": "Hardware",
        "cost_price": 50.00,
        "retail_price": 100.00,
        "stock_quantity": 25,
        "supplier_id": "SUPP_1",
        "created_at": "2025-01-01 00:00:00",
        "updated_at": "2025-01-01 00:00:00"
    }])

    transformer.load_product_dimension(prods)
    df = test_db.query_to_df("SELECT * FROM dim_product WHERE product_id = 'PROD_T1'")
    assert len(df) == 1
    row = df.iloc[0]
    assert row["margin_amount"] == 50.00
    assert row["margin_percentage"] == 50.00
