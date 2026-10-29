import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# Directories
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
RAW_BATCH_1_DIR = RAW_DATA_DIR / "batch_1_initial"
RAW_BATCH_2_DIR = RAW_DATA_DIR / "batch_2_incremental"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
WAREHOUSE_DIR = DATA_DIR / "warehouse"
POWERBI_EXPORT_DIR = DATA_DIR / "power_bi_export"
QUALITY_REPORTS_DIR = DATA_DIR / "quality_reports"
LOGS_DIR = BASE_DIR / "logs"
SQL_DIR = BASE_DIR / "sql"

for d in [
    DATA_DIR, RAW_DATA_DIR, RAW_BATCH_1_DIR, RAW_BATCH_2_DIR,
    PROCESSED_DATA_DIR, WAREHOUSE_DIR, POWERBI_EXPORT_DIR,
    QUALITY_REPORTS_DIR, LOGS_DIR
]:
    d.mkdir(parents=True, exist_ok=True)

# Database Configuration
DB_DIALECT = os.getenv("DB_DIALECT", "postgres").lower()
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "ecommerce_dw")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
SQLITE_DB_PATH = BASE_DIR / os.getenv("SQLITE_PATH", "data/warehouse/ecommerce_dw.db")

# Logging setup
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

def setup_logger(name: str = "ecommerce_pipeline") -> logging.Logger:
    """Configures structured console and file logging."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
        
        # File handler
        log_file = LOGS_DIR / "pipeline.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger

logger = setup_logger()

def get_db_url(force_sqlite: bool = False):
    """
    Returns the database connection URL.
    Attempts PostgreSQL if configured, falls back to local SQLite if unreachable.
    """
    if force_sqlite or DB_DIALECT == "sqlite":
        return f"sqlite:///{SQLITE_DB_PATH}"
    
    return f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

_cached_engine = None

def get_engine(force_sqlite: bool = False):
    """
    Creates and returns a SQLAlchemy engine.
    Gracefully falls back to SQLite if PostgreSQL connection fails.
    Caches engine to avoid repeated connection timeouts.
    """
    global _cached_engine
    if _cached_engine is not None and not force_sqlite:
        return _cached_engine

    if force_sqlite or DB_DIALECT == "sqlite":
        logger.info(f"Connecting to SQLite Data Warehouse at: {SQLITE_DB_PATH}")
        _cached_engine = create_engine(f"sqlite:///{SQLITE_DB_PATH}")
        return _cached_engine
    
    # Try PostgreSQL
    pg_url = get_db_url(force_sqlite=False)
    try:
        engine = create_engine(pg_url, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Successfully connected to PostgreSQL at {DB_HOST}:{DB_PORT}/{DB_NAME}")
        _cached_engine = engine
        return _cached_engine
    except Exception as e:
        logger.warning(
            f"Could not connect to PostgreSQL ({e}). "
            f"Falling back to local SQLite Data Warehouse at: {SQLITE_DB_PATH}"
        )
        _cached_engine = create_engine(f"sqlite:///{SQLITE_DB_PATH}")
        return _cached_engine
