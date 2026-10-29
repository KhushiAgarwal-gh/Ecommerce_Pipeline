"""
Unit Tests for SCD Type 2 Handler
Validates version history preservation, valid_from/to ranges, and point-in-time lookups.
"""
import pytest
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine

from src.db_manager import DatabaseManager
from src.scd2_handler import SCD2Handler


@pytest.fixture
def test_db(tmp_path):
    """Creates a temporary in-memory/file SQLite test database."""
    db_file = tmp_path / "test_dw.db"
    engine = create_engine(f"sqlite:///{db_file}")
    db = DatabaseManager(engine=engine, force_sqlite=True)
    db.init_schema(drop_first=True)
    return db


def test_scd2_initial_insert(test_db):
    scd = SCD2Handler(test_db)
    customers = pd.DataFrame([{
        "customer_id": "CUST_TEST_1",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "phone": "1234567890",
        "street": "100 Broadway",
        "city": "New York",
        "state": "NY",
        "postal_code": "10001",
        "country": "USA",
        "created_at": "2025-01-01 10:00:00",
        "updated_at": "2025-01-01 10:00:00"
    }])

    res = scd.process_customers_scd2(customers)
    assert res["new_customers"] == 1
    assert res["updated_scd2_versions"] == 0

    df = test_db.query_to_df("SELECT * FROM dim_customer WHERE customer_id = 'CUST_TEST_1'")
    assert len(df) == 1
    assert df.iloc[0]["version"] == 1
    assert df.iloc[0]["is_current"] == 1
    assert df.iloc[0]["city"] == "New York"


def test_scd2_address_update_and_pit_lookup(test_db):
    scd = SCD2Handler(test_db)
    
    # 1. Insert Version 1 in Jan 2025
    v1 = pd.DataFrame([{
        "customer_id": "CUST_TEST_2",
        "first_name": "Jane",
        "last_name": "Roe",
        "email": "jane@example.com",
        "phone": "5551112222",
        "street": "100 Market St",
        "city": "San Francisco",
        "state": "CA",
        "postal_code": "94105",
        "country": "USA",
        "created_at": "2025-01-15 09:00:00",
        "updated_at": "2025-01-15 09:00:00"
    }])
    scd.process_customers_scd2(v1)

    # 2. Update address in July 2025 (moves to Austin, TX)
    v2 = pd.DataFrame([{
        "customer_id": "CUST_TEST_2",
        "first_name": "Jane",
        "last_name": "Roe",
        "email": "jane@example.com",
        "phone": "5551112222",
        "street": "500 Congress Ave",
        "city": "Austin",
        "state": "TX",
        "postal_code": "78701",
        "country": "USA",
        "created_at": "2025-01-15 09:00:00",
        "updated_at": "2025-07-01 14:00:00"
    }])
    res = scd.process_customers_scd2(v2)
    assert res["updated_scd2_versions"] == 1

    # Verify 2 records exist in dim_customer
    history_df = test_db.query_to_df("SELECT * FROM dim_customer WHERE customer_id = 'CUST_TEST_2' ORDER BY version")
    assert len(history_df) == 2

    # Version 1 check
    row_v1 = history_df.iloc[0]
    assert row_v1["version"] == 1
    assert row_v1["is_current"] == 0
    assert row_v1["city"] == "San Francisco"
    assert row_v1["valid_to"] == "2025-07-01 14:00:00"

    # Version 2 check
    row_v2 = history_df.iloc[1]
    assert row_v2["version"] == 2
    assert row_v2["is_current"] == 1
    assert row_v2["city"] == "Austin"
    assert row_v2["valid_from"] == "2025-07-01 14:00:00"
    assert "9999" in row_v2["valid_to"]

    # 3. Test Point-In-Time Surrogate Key Lookups
    # A purchase in March 2025 should map to Version 1 (San Francisco)
    march_key = scd.get_customer_key_as_of("CUST_TEST_2", "2025-03-20 12:00:00")
    assert march_key == row_v1["dim_customer_key"]

    # A purchase in August 2025 should map to Version 2 (Austin)
    august_key = scd.get_customer_key_as_of("CUST_TEST_2", "2025-08-15 12:00:00")
    assert august_key == row_v2["dim_customer_key"]
