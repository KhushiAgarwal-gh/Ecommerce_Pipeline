"""
Airflow Local DAG Execution Harness
Simulates and executes Apache Airflow DAGs locally on Windows without Docker or external daemons.
Follows topological task execution, logging, state transitions, and dependency validation.
"""
import sys
import time
from pathlib import Path
from datetime import datetime

# Add root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import logger
from dags.ecommerce_etl_dag import (
    task_check_source_files,
    task_ingest_and_clean,
    task_load_dimensions,
    task_process_scd2_customers,
    task_load_facts,
    task_quality_audit,
    task_export_powerbi,
)


class AirflowLocalRunner:
    """Executes Airflow DAG tasks locally with dependency tracking and status logs."""

    def __init__(self, dag_id: str = "ecommerce_end_to_end_etl_pipeline", batch_type: str = "initial"):
        self.dag_id = dag_id
        self.batch_type = batch_type

        # Define DAG task execution plan in topological order
        self.tasks = [
            ("check_source_files", task_check_source_files, {"batch_type": self.batch_type}),
            ("ingest_and_clean_data", task_ingest_and_clean, {"batch_type": self.batch_type}),
            ("load_reference_and_product_dimensions", task_load_dimensions, {}),
            ("process_scd2_customers", task_process_scd2_customers, {}),
            ("load_fact_tables", task_load_facts, {"batch_type": self.batch_type}),
            ("run_warehouse_quality_audit", task_quality_audit, {}),
            ("export_powerbi_reporting_layer", task_export_powerbi, {})
        ]

    def run(self):
        """Executes all DAG tasks in sequence, reporting task status, duration, and results."""
        print("=" * 80)
        print(f"  APACHE AIRFLOW DAG EXECUTION HARNESS")
        print(f"  DAG ID     : {self.dag_id}")
        print(f"  Run ID     : manual__{datetime.now().strftime('%Y-%m-%dT%H%M%S')}")
        print(f"  Batch Type : {self.batch_type.upper()}")
        print("=" * 80)

        dag_start_time = time.time()
        task_metrics = []

        for task_id, callable_fn, kwargs in self.tasks:
            print(f"\n[AIRFLOW ENGINE] Task '{task_id}' -> State: QUEUED")
            time.sleep(0.3)
            print(f"[AIRFLOW ENGINE] Task '{task_id}' -> State: RUNNING")
            task_start = time.time()

            try:
                result = callable_fn(**kwargs)
                task_duration = round(time.time() - task_start, 2)
                print(f"[AIRFLOW ENGINE] Task '{task_id}' -> State: SUCCESS (took {task_duration}s)")
                task_metrics.append({"task_id": task_id, "status": "SUCCESS", "duration_sec": task_duration})
            except Exception as e:
                task_duration = round(time.time() - task_start, 2)
                print(f"[AIRFLOW ENGINE] Task '{task_id}' -> State: FAILED (took {task_duration}s)")
                print(f"[AIRFLOW ENGINE] Error Details: {e}")
                task_metrics.append({"task_id": task_id, "status": "FAILED", "duration_sec": task_duration, "error": str(e)})
                print("\n" + "=" * 80)
                print(f"  DAG RUN TERMINATED WITH ERRORS AT TASK: {task_id}")
                print("=" * 80)
                raise e

        dag_total_duration = round(time.time() - dag_start_time, 2)
        print("\n" + "=" * 80)
        print(f"  DAG RUN COMPLETED SUCCESSFULLY in {dag_total_duration}s")
        print("=" * 80)
        for m in task_metrics:
            print(f"  - {m['task_id']:<45} : {m['status']} ({m['duration_sec']}s)")
        print("=" * 80)
        return task_metrics


if __name__ == "__main__":
    batch = sys.argv[1] if len(sys.argv) > 1 else "initial"
    runner = AirflowLocalRunner(batch_type=batch)
    runner.run()
