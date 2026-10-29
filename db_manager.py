"""
Database Manager Module
Handles database initialization, DDL execution, transaction management, and query helpers.
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
from sqlalchemy import text, Engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import get_engine, SQL_DIR, logger


class DatabaseManager:
    """Encapsulates database operations for both PostgreSQL and SQLite."""

    def __init__(self, engine: Optional[Engine] = None, force_sqlite: bool = False):
        self.engine = engine if engine else get_engine(force_sqlite=force_sqlite)
        self.dialect = self.engine.dialect.name  # 'postgresql' or 'sqlite'
        logger.info(f"DatabaseManager initialized with dialect: {self.dialect}")

    def init_schema(self, drop_first: bool = False):
        """Executes the appropriate DDL script to create warehouse tables."""
        ddl_file = SQL_DIR / ("ddl_postgres.sql" if self.dialect == "postgresql" else "ddl_sqlite.sql")
        logger.info(f"Applying DDL schema from {ddl_file.name} (drop_first={drop_first})...")

        if drop_first:
            self._drop_all_tables()

        with open(ddl_file, "r", encoding="utf-8") as f:
            ddl_script = f.read()

        # Split and execute individual statements
        statements = [stmt.strip() for stmt in ddl_script.split(";") if stmt.strip()]
        with self.engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))

        logger.info("Database schema initialized successfully.")

    def _drop_all_tables(self):
        """Drops all warehouse tables in reverse dependency order."""
        tables = [
            "fact_returns", "fact_sales", "dim_customer",
            "dim_product", "dim_payment_method", "dim_order_status",
            "dim_date", "etl_watermark"
        ]
        with self.engine.begin() as conn:
            for tbl in tables:
                if self.dialect == "postgresql":
                    conn.execute(text(f"DROP TABLE IF EXISTS {tbl} CASCADE;"))
                else:
                    conn.execute(text(f"DROP TABLE IF EXISTS {tbl};"))
        logger.info("All existing warehouse tables dropped.")

    def execute(self, sql_query: str, params: Optional[Dict[str, Any]] = None):
        """Executes a SQL command within a transaction."""
        with self.engine.begin() as conn:
            result = conn.execute(text(sql_query), params or {})
            return result

    def query_to_df(self, sql_query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Executes a SQL SELECT query and returns the results as a pandas DataFrame."""
        with self.engine.connect() as conn:
            df = pd.read_sql_query(text(sql_query), conn, params=params)
            return df

    def insert_dataframe(self, table_name: str, df: pd.DataFrame, if_exists: str = "append", chunksize: int = 1000):
        """Bulk inserts a pandas DataFrame into the specified table."""
        if df.empty:
            logger.info(f"DataFrame for table '{table_name}' is empty. Skipping insertion.")
            return 0

        logger.info(f"Writing {len(df)} records into table '{table_name}' (mode: {if_exists})...")
        df.to_sql(
            table_name,
            self.engine,
            if_exists=if_exists,
            index=False,
            chunksize=chunksize,
            method="multi" if self.dialect == "sqlite" else None
        )
        logger.info(f"Successfully inserted {len(df)} records into '{table_name}'.")
        return len(df)

    def get_watermark(self, table_name: str) -> Optional[str]:
        """Retrieves the last processed timestamp watermark for a table."""
        query = "SELECT last_processed_timestamp FROM etl_watermark WHERE table_name = :tbl"
        df = self.query_to_df(query, {"tbl": table_name})
        if not df.empty and pd.notna(df.iloc[0]["last_processed_timestamp"]):
            return str(df.iloc[0]["last_processed_timestamp"])
        return None

    def update_watermark(self, table_name: str, last_timestamp: str, records: int, batch_id: str):
        """Upserts watermark tracking information for a table."""
        if self.dialect == "postgresql":
            sql = """
                INSERT INTO etl_watermark (table_name, last_processed_timestamp, records_processed, batch_id, last_run_at)
                VALUES (:tbl, :ts, :recs, :batch, CURRENT_TIMESTAMP)
                ON CONFLICT (table_name) DO UPDATE SET
                    last_processed_timestamp = EXCLUDED.last_processed_timestamp,
                    records_processed = etl_watermark.records_processed + EXCLUDED.records_processed,
                    batch_id = EXCLUDED.batch_id,
                    last_run_at = EXCLUDED.last_run_at;
            """
        else:
            sql = """
                INSERT INTO etl_watermark (table_name, last_processed_timestamp, records_processed, batch_id, last_run_at)
                VALUES (:tbl, :ts, :recs, :batch, datetime('now'))
                ON CONFLICT(table_name) DO UPDATE SET
                    last_processed_timestamp = excluded.last_processed_timestamp,
                    records_processed = etl_watermark.records_processed + excluded.records_processed,
                    batch_id = excluded.batch_id,
                    last_run_at = excluded.last_run_at;
            """
        self.execute(sql, {"tbl": table_name, "ts": last_timestamp, "recs": records, "batch": batch_id})

    def get_table_count(self, table_name: str) -> int:
        """Returns the total row count of a table."""
        df = self.query_to_df(f"SELECT COUNT(*) AS cnt FROM {table_name}")
        return int(df.iloc[0]["cnt"])


if __name__ == "__main__":
    db = DatabaseManager(force_sqlite=True)
    db.init_schema(drop_first=True)
    print("Schema initialized successfully!")
