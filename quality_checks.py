"""
Data Quality Validation Framework
Executes automated pre-load and post-load assertions on schema, constraints,
referential integrity, SCD Type 2 consistency, and financial reconciliations.
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db_manager import DatabaseManager
from src.config import QUALITY_REPORTS_DIR, logger


class QualityCheckResult:
    def __init__(self, check_name: str, passed: bool, details: str, severity: str = "ERROR"):
        self.check_name = check_name
        self.passed = passed
        self.details = details
        self.severity = severity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "status": "PASSED" if self.passed else "FAILED",
            "details": self.details,
            "severity": self.severity
        }


class DataQualityAuditor:
    """Runs data quality test suites and writes audit summary reports."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def audit_warehouse(self) -> Dict[str, Any]:
        """Runs the complete suite of analytical warehouse data quality assertions."""
        logger.info("Executing Data Warehouse Quality Audit Suite...")
        results: List[QualityCheckResult] = []

        # 1. Row count checks
        tables = ["dim_date", "dim_customer", "dim_product", "dim_payment_method", "dim_order_status", "fact_sales", "fact_returns"]
        for tbl in tables:
            cnt = self.db.get_table_count(tbl)
            passed = cnt > 0
            results.append(QualityCheckResult(
                check_name=f"volume_check_{tbl}",
                passed=passed,
                details=f"Table {tbl} has {cnt} rows."
            ))

        # 2. Fact Sales Foreign Key Null Checks
        fk_columns = ["dim_customer_key", "dim_product_key", "dim_order_date_key", "dim_payment_key", "dim_status_key"]
        for col in fk_columns:
            query = f"SELECT COUNT(*) AS null_cnt FROM fact_sales WHERE {col} IS NULL"
            null_cnt = int(self.db.query_to_df(query).iloc[0]["null_cnt"])
            results.append(QualityCheckResult(
                check_name=f"fact_sales_not_null_{col}",
                passed=(null_cnt == 0),
                details=f"Found {null_cnt} NULL foreign keys in fact_sales.{col}."
            ))

        # 3. Fact Sales Referential Integrity
        ri_checks = [
            ("dim_customer_key", "dim_customer", "dim_customer_key"),
            ("dim_product_key", "dim_product", "dim_product_key"),
            ("dim_order_date_key", "dim_date", "date_key"),
            ("dim_payment_key", "dim_payment_method", "dim_payment_key"),
            ("dim_status_key", "dim_order_status", "dim_status_key"),
        ]
        for fact_col, dim_tbl, dim_col in ri_checks:
            query = f"""
                SELECT COUNT(*) AS orphan_cnt
                FROM fact_sales f
                LEFT JOIN {dim_tbl} d ON f.{fact_col} = d.{dim_col}
                WHERE d.{dim_col} IS NULL
            """
            orphan_cnt = int(self.db.query_to_df(query).iloc[0]["orphan_cnt"])
            results.append(QualityCheckResult(
                check_name=f"referential_integrity_{fact_col}_to_{dim_tbl}",
                passed=(orphan_cnt == 0),
                details=f"Found {orphan_cnt} orphaned records linking fact_sales.{fact_col} -> {dim_tbl}."
            ))

        # 4. SCD Type 2 Integrity: At most ONE active record per customer_id
        scd2_query = """
            SELECT customer_id, COUNT(*) AS active_cnt
            FROM dim_customer
            WHERE is_current = 1 OR is_current = TRUE
            GROUP BY customer_id
            HAVING COUNT(*) > 1
        """
        scd2_violations = self.db.query_to_df(scd2_query)
        passed_scd2 = len(scd2_violations) == 0
        results.append(QualityCheckResult(
            check_name="scd2_single_active_version_check",
            passed=passed_scd2,
            details=f"Found {len(scd2_violations)} customers with multiple active SCD2 versions."
        ))

        # 5. Financial Reconciliation: net_revenue == gross_amount - discount_amount
        recon_query = """
            SELECT COUNT(*) AS mismatch_cnt
            FROM fact_sales
            WHERE ABS(net_revenue - (gross_amount - discount_amount)) > 0.05
        """
        mismatches = int(self.db.query_to_df(recon_query).iloc[0]["mismatch_cnt"])
        results.append(QualityCheckResult(
            check_name="financial_reconciliation_net_revenue",
            passed=(mismatches == 0),
            details=f"Found {mismatches} records with net_revenue formula mismatches."
        ))

        # 6. Uniqueness of Primary Grain
        dup_query = """
            SELECT order_item_id, COUNT(*) AS cnt
            FROM fact_sales
            GROUP BY order_item_id
            HAVING COUNT(*) > 1
        """
        dups = self.db.query_to_df(dup_query)
        results.append(QualityCheckResult(
            check_name="fact_sales_order_item_uniqueness",
            passed=(len(dups) == 0),
            details=f"Found {len(dups)} duplicate order_item_id entries in fact_sales."
        ))

        # Summary computation
        total_checks = len(results)
        passed_checks = sum(1 for r in results if r.passed)
        failed_checks = total_checks - passed_checks

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "overall_status": "PASSED" if failed_checks == 0 else "FAILED",
            "checks": [r.to_dict() for r in results]
        }

        # Write quality report to disk
        report_file = QUALITY_REPORTS_DIR / f"quality_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        latest_file = QUALITY_REPORTS_DIR / "latest_quality_report.json"
        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Quality audit completed: {passed_checks}/{total_checks} PASSED. (Report: {latest_file.name})")

        if failed_checks > 0:
            failed_names = [r.check_name for r in results if not r.passed]
            logger.error(f"Data quality checks FAILED on: {failed_names}")

        return summary
