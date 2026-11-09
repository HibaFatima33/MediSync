"""
Four Airflow tasks:
1. Read files into PostgreSQL staging.
2. Check, transform and load the data mart.
3. Run the three SQL questions.
4. Rebuild the dashboard.

The old pharma_phase1 DAG stays unchanged.
"""

import json
import os
import urllib.error
import urllib.request

from datetime import datetime, timedelta, timezone
from airflow.sdk import dag, task


def call_api(endpoint, body):
    base_url = os.environ.get(
        "PHARMA_API_URL",
        "http://172.17.128.1:8765"
    )

    request = urllib.request.Request(
        base_url.rstrip("/") + endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=1800
        ) as response:
            return json.load(response)

    except urllib.error.HTTPError as error:
        details = error.read().decode(
            "utf-8",
            errors="replace"
        )

        raise RuntimeError(
            f"API request failed: {details}"
        ) from error


@dag(
    dag_id="sales_demand_visuals",
    start_date=datetime(
        2026, 1, 1,
        tzinfo=timezone.utc
    ),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 1,
        "retry_delay": timedelta(minutes=1)
    },
    tags=["Hiba", "Bilqees", "Phase1"]
)
def refresh_pipeline():

    @task
    def ingest_into_postgres():
        result = call_api(
            "/ingest",
            {"require_postgres": True}
        )

        return result["snapshot"]

    @task
    def validate_transform_and_load(snapshot):
        result = call_api(
            "/load",
            {"snapshot": snapshot}
        )

        return {
            "batch": result["batch"],
            "counts": result["table_counts"]
        }

    @task
    def execute_three_questions(load_result):
        return call_api("/queries", {})

    @task
    def refresh_dashboard(query_result):
        return call_api("/dashboard", {})

    snapshot = ingest_into_postgres()

    loaded = validate_transform_and_load(
        snapshot
    )

    answers = execute_three_questions(
        loaded
    )

    refresh_dashboard(answers)


refresh_pipeline()