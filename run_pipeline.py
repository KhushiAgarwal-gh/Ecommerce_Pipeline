"""
E-Commerce Pipeline Master CLI Runner
Executes the end-to-end data engineering pipeline locally or in production.
"""
import sys
import argparse
import time
from pathlib import Path
# Add root directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import logger, SQL_DIR
from src.db_manager import DatabaseManager
from src.ingest import DataIngestor
from src.clean_validate import DataCleaner
from src.incremental_loader import IncrementalLoader
from src.quality_checks import DataQualityAuditor
from src.powerbi_export import export_powerbi_data
from src.generator import generate_all_datasets


def print_banner():
    banner = """
================================================================================
       E-COMMERCE END-TO-END DATA ENGINEERING PIPELINE (STAR SCHEMA & SCD2)
================================================================================
    """
    print(banner)


def run_etl_batch(db: DatabaseManager, batch_type: str = "initial"):
    """Executes ingestion, cleaning, dimensional modeling, and loading for a batch."""
    logger.info(f">>> Launching ETL for batch: {batch_type.upper()} <<<")
    start_time = time.time()

    # Step 1: Ingestion
    ingestor = DataIngestor(batch_type=batch_type)
    raw_data = ingestor.ingest_batch()

    # Step 2: Cleaning & Validation
    cleaner = DataCleaner()
    cleaned_data = cleaner.clean_all(raw_data)

    # Step 3: Warehouse Loading (Dimensions, SCD2, Facts, Watermarks)
    loader = IncrementalLoader(db)
    if batch_type in ["initial", "batch_1"]:
        metrics = loader.load_initial_batch(cleaned_data)
    else:
        metrics = loader.load_incremental_batch(cleaned_data)

    duration = round(time.time() - start_time, 2)
    logger.info(f">>> Batch {batch_type.upper()} completed in {duration}s <<<")
    print(f"\n[SUMMARY] Batch {batch_type.upper()} Metrics:")
    for k, v in metrics.items():
        print(f"  * {k}: {v}")
    print()
    return metrics


def run_analytical_queries(db: DatabaseManager):
    """Executes high-value business analytical queries from sql/analytical_queries.sql."""
    print("\n" + "=" * 80)
    print("  EXECUTING ADVANCED SQL ANALYTICAL QUERIES ON DATA WAREHOUSE")
    print("=" * 80)

    queries_file = SQL_DIR / "analytical_queries.sql"
    with open(queries_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by double newline and comment headers
    blocks = content.split("-- ----------------------------------------------------------------------------")
    
    query_num = 1
    for block in blocks:
        lines = [line for line in block.strip().split("\n") if line.strip() and not line.strip().startswith("--")]
        comment_lines = [line.replace("--", "").strip() for line in block.strip().split("\n") if line.strip().startswith("--")]
        if not lines:
            continue
        
        title = comment_lines[0] if comment_lines else f"Query {query_num}"
        sql_query = "\n".join(lines).strip().rstrip(";")

        print(f"\n[QUERY {query_num}] {title}")
        print("-" * 80)
        try:
            df = db.query_to_df(sql_query)
            if df.empty:
                print("No rows returned.")
            else:
                # Print preview (top 5 rows)
                print(df.head(6).to_string(index=False))
                if len(df) > 6:
                    print(f"... ({len(df)} total rows returned)")
            query_num += 1
        except Exception as e:
            print(f"Error executing query: {e}")

    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(description="E-Commerce End-to-End Data Engineering Pipeline")
    parser.add_argument(
        "--batch",
        choices=["initial", "incremental", "full"],
        default="full",
        help="Batch mode to run: initial (Batch 1), incremental (Batch 2), or full (Batch 1 + 2)"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate data warehouse schema before running"
    )
    parser.add_argument(
        "--generate-data",
        action="store_true",
        help="Regenerate synthetic raw datasets before executing"
    )
    parser.add_argument(
        "--queries",
        action="store_true",
        help="Execute analytical queries after ETL completion"
    )
    parser.add_argument(
        "--sqlite",
        action="store_true",
        help="Force SQLite data warehouse engine (bypasses PostgreSQL)"
    )
    parser.add_argument(
        "--quality-only",
        action="store_true",
        help="Only run warehouse data quality checks"
    )
    parser.add_argument(
        "--export-powerbi",
        action="store_true",
        help="Export curated datasets for Power BI"
    )

    args = parser.parse_args()
    print_banner()

    # Step 0: Data Generation if requested or if raw data is missing
    batch_1_file = PROJECT_ROOT / "data" / "raw" / "batch_1_initial" / "orders.csv"
    if args.generate_data or not batch_1_file.exists():
        logger.info("Generating realistic sample data files...")
        generate_all_datasets()

    # Step 1: Database Initialization
    db = DatabaseManager(force_sqlite=args.sqlite)

    if args.quality_only:
        auditor = DataQualityAuditor(db)
        auditor.audit_warehouse()
        return

    if args.reset or args.batch in ["initial", "full"]:
        logger.info("Initializing Data Warehouse schema (drop_first=True)...")
        db.init_schema(drop_first=True)
        # Apply semantic views
        views_file = SQL_DIR / "views.sql"
        if views_file.exists():
            with open(views_file, "r", encoding="utf-8") as f:
                views_sql = f.read()
            for stmt in views_sql.split(";"):
                if stmt.strip():
                    try:
                        db.execute(stmt)
                    except Exception as e:
                        logger.warning(f"View creation note: {e}")

    # Step 2: Execute Batch(es)
    if args.batch == "initial":
        run_etl_batch(db, batch_type="initial")
    elif args.batch == "incremental":
        run_etl_batch(db, batch_type="incremental")
    elif args.batch == "full":
        print("\n>>> PHASE 1: Running Batch 1 (Initial Load) <<<")
        run_etl_batch(db, batch_type="initial")
        print("\n>>> PHASE 2: Running Batch 2 (Incremental Load with SCD Type 2) <<<")
        run_etl_batch(db, batch_type="incremental")

    # Step 3: Automated Quality Audit
    print("\n>>> PHASE 3: Executing Data Warehouse Quality Audit <<<")
    auditor = DataQualityAuditor(db)
    summary = auditor.audit_warehouse()
    print(f"\n[AUDIT RESULT] Status: {summary['overall_status']} | Passed: {summary['passed_checks']}/{summary['total_checks']}")

    # Step 4: Power BI Export
    print("\n>>> PHASE 4: Exporting Curated Layer for Power BI <<<")
    export_powerbi_data(db)

    # Step 5: Analytical SQL Queries
    if args.queries or args.batch == "full":
        run_analytical_queries(db)

    print("\n" + "=" * 80)
    print("  ALL PIPELINE STAGES COMPLETED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()
