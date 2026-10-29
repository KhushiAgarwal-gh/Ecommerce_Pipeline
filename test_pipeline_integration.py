"""
End-to-End Pipeline Integration Tests
Validates full ETL lifecycle, watermark tracking, incremental updates, and quality checks.
"""
import pytest
from sqlalchemy import create_engine

from src.ingest import DataIngestor
from src.clean_validate import DataCleaner
from src.db_manager import DatabaseManager
from src.incremental_loader import IncrementalLoader
from src.quality_checks import DataQualityAuditor


@pytest.fixture
def clean_test_db(tmp_path):
    test_db_file = tmp_path / "integration_dw.db"
    engine = create_engine(f"sqlite:///{test_db_file}")
    db = DatabaseManager(engine=engine, force_sqlite=True)
    db.init_schema(drop_first=True)
    return db


def test_full_pipeline_lifecycle(clean_test_db):
    db = clean_test_db
    loader = IncrementalLoader(db)
    cleaner = DataCleaner()

    # 1. Batch 1 Initial Load
    ingestor_1 = DataIngestor(batch_type="initial")
    raw_1 = ingestor_1.ingest_batch()
    clean_1 = cleaner.clean_all(raw_1)

    init_metrics = loader.load_initial_batch(clean_1)
    assert init_metrics["customers_loaded"] > 0
    assert init_metrics["sales_records"] > 0

    watermark_1 = db.get_watermark("fact_sales")
    assert watermark_1 is not None

    # 2. Batch 2 Incremental Load
    ingestor_2 = DataIngestor(batch_type="incremental")
    raw_2 = ingestor_2.ingest_batch()
    clean_2 = cleaner.clean_all(raw_2)

    inc_metrics = loader.load_incremental_batch(clean_2)
    assert inc_metrics["scd2_updated_versions"] > 0
    assert inc_metrics["orders_updated"] > 0

    watermark_2 = db.get_watermark("fact_sales")
    assert watermark_2 >= watermark_1

    # 3. Data Warehouse Quality Audit
    auditor = DataQualityAuditor(db)
    summary = auditor.audit_warehouse()
    assert summary["overall_status"] == "PASSED"
    assert summary["failed_checks"] == 0
    assert summary["passed_checks"] == summary["total_checks"]
