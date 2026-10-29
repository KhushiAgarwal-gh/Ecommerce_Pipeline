"""
Slowly Changing Dimension (SCD) Type 2 Handler
Maintains historical customer states, handles attribute delta detection, expires older records,
and provides point-in-time surrogate key lookups for Kimball dimensional fact modeling.
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db_manager import DatabaseManager
from src.config import logger

# Attributes that trigger a new SCD Type 2 version upon change
TRACKED_ATTRIBUTES = ["street", "city", "state", "postal_code", "phone"]


class SCD2Handler:
    """Manages Slowly Changing Dimension Type 2 lifecycle for dim_customer."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def process_customers_scd2(self, incoming_customers: pd.DataFrame) -> Dict[str, int]:
        """
        Processes incoming customer records against dim_customer:
        - Detects new customers -> inserts version 1
        - Detects attribute changes in existing customers -> expires active version & inserts version N+1
        - Unchanged customers -> skipped
        """
        logger.info(f"Processing {len(incoming_customers)} customer records with SCD Type 2...")

        # Retrieve all currently active customer records from dim_customer
        active_query = """
            SELECT dim_customer_key, customer_id, first_name, last_name, email,
                   phone, street, city, state, postal_code, country, version
            FROM dim_customer
            WHERE is_current = 1 OR is_current = TRUE
        """
        active_df = self.db.query_to_df(active_query)
        active_map = {}
        if not active_df.empty:
            for _, row in active_df.iterrows():
                active_map[row["customer_id"]] = row.to_dict()

        new_records_to_insert = []
        keys_to_expire = []
        expire_timestamps = []

        new_count = 0
        updated_count = 0
        unchanged_count = 0

        # Query max existing surrogate key to assign unique incremental keys
        max_key_df = self.db.query_to_df("SELECT COALESCE(MAX(dim_customer_key), 0) AS max_key FROM dim_customer")
        current_surrogate_key = int(max_key_df.iloc[0]["max_key"])

        for _, inc in incoming_customers.iterrows():
            cust_id = inc["customer_id"]
            cust_ts = str(inc.get("updated_at", inc.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))))

            if cust_id not in active_map:
                # 1. Brand new customer -> Version 1
                current_surrogate_key += 1
                new_records_to_insert.append({
                    "dim_customer_key": current_surrogate_key,
                    "customer_id": cust_id,
                    "first_name": inc["first_name"],
                    "last_name": inc["last_name"],
                    "full_name": f"{inc['first_name']} {inc['last_name']}".strip(),
                    "email": inc["email"],
                    "phone": inc.get("phone", ""),
                    "street": inc.get("street", ""),
                    "city": inc.get("city", ""),
                    "state": inc.get("state", ""),
                    "postal_code": inc.get("postal_code", ""),
                    "country": inc.get("country", "USA"),
                    "valid_from": str(inc["created_at"]),
                    "valid_to": "9999-12-31 23:59:59",
                    "is_current": 1 if self.db.dialect == "sqlite" else True,
                    "version": 1
                })
                new_count += 1
            else:
                # 2. Existing customer -> check for tracked attribute changes
                existing = active_map[cust_id]
                has_changed = False
                for attr in TRACKED_ATTRIBUTES:
                    inc_val = str(inc.get(attr, "")).strip().lower()
                    exist_val = str(existing.get(attr, "")).strip().lower()
                    if inc_val != exist_val:
                        has_changed = True
                        break

                if has_changed:
                    # Expire currently active record
                    keys_to_expire.append(existing["dim_customer_key"])
                    expire_timestamps.append(cust_ts)

                    # Insert new active version
                    current_surrogate_key += 1
                    new_version = int(existing["version"]) + 1
                    new_records_to_insert.append({
                        "dim_customer_key": current_surrogate_key,
                        "customer_id": cust_id,
                        "first_name": inc["first_name"],
                        "last_name": inc["last_name"],
                        "full_name": f"{inc['first_name']} {inc['last_name']}".strip(),
                        "email": inc["email"],
                        "phone": inc.get("phone", ""),
                        "street": inc.get("street", ""),
                        "city": inc.get("city", ""),
                        "state": inc.get("state", ""),
                        "postal_code": inc.get("postal_code", ""),
                        "country": inc.get("country", "USA"),
                        "valid_from": cust_ts,
                        "valid_to": "9999-12-31 23:59:59",
                        "is_current": 1 if self.db.dialect == "sqlite" else True,
                        "version": new_version
                    })
                    updated_count += 1
                else:
                    unchanged_count += 1

        # Execute expiring updates in transaction
        if keys_to_expire:
            logger.info(f"Expiring {len(keys_to_expire)} historical customer versions...")
            for key, exp_ts in zip(keys_to_expire, expire_timestamps):
                if self.db.dialect == "postgresql":
                    expire_sql = """
                        UPDATE dim_customer
                        SET is_current = FALSE, valid_to = :exp_ts
                        WHERE dim_customer_key = :k;
                    """
                else:
                    expire_sql = """
                        UPDATE dim_customer
                        SET is_current = 0, valid_to = :exp_ts
                        WHERE dim_customer_key = :k;
                    """
                self.db.execute(expire_sql, {"k": key, "exp_ts": exp_ts})

        # Insert new rows
        if new_records_to_insert:
            insert_df = pd.DataFrame(new_records_to_insert)
            self.db.insert_dataframe("dim_customer", insert_df, if_exists="append")

        logger.info(f"SCD2 Processing complete: {new_count} new, {updated_count} updated (new versions), {unchanged_count} unchanged.")
        return {
            "new_customers": new_count,
            "updated_scd2_versions": updated_count,
            "unchanged_customers": unchanged_count
        }

    def get_customer_key_as_of(self, customer_id: str, as_of_timestamp: str) -> Optional[int]:
        """
        Point-in-time surrogate key lookup:
        Finds the dim_customer_key valid at the exact time the event/order occurred.
        """
        query = """
            SELECT dim_customer_key
            FROM dim_customer
            WHERE customer_id = :cid
              AND valid_from <= :ts
              AND valid_to >= :ts
            ORDER BY valid_from DESC
            LIMIT 1
        """
        df = self.db.query_to_df(query, {"cid": customer_id, "ts": str(as_of_timestamp)})
        if not df.empty:
            return int(df.iloc[0]["dim_customer_key"])

        # Fallback to active key if exact match not found (e.g. edge timestamp)
        fallback = self.db.query_to_df(
            "SELECT dim_customer_key FROM dim_customer WHERE customer_id = :cid ORDER BY version DESC LIMIT 1",
            {"cid": customer_id}
        )
        if not fallback.empty:
            return int(fallback.iloc[0]["dim_customer_key"])
        return None
