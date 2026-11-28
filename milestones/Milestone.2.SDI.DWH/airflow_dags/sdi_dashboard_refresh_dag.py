"""Four tasks from optional new-month generation through the SQL answer layer; Power BI refresh is done separately in Desktop."""
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from airflow.sdk import Param, dag, get_current_context, task


def call_api(endpoint, body):
    base_url = os.environ.get("PHARMA_API_URL", "http://172.17.128.1:8765")
    request = urllib.request.Request(
        base_url.rstrip("/") + endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=1800) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError("API request failed: " + error.read().decode("utf-8", errors="replace")) from error


@dag(
    dag_id="sales_demand_visuals",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=1)},
    params={
        "generate_new_data": Param(False, type="boolean", title="Generate the next month", description="Turn on for a new-data refresh. Leave off to reload existing files or use the watcher."),
        "sales_rows": Param(1000, type="integer", minimum=1, maximum=10000, title="New sales rows")
    },
    tags=["Hiba", "Bilqees", "Phase1"]
)
def refresh_pipeline():
    @task
    def generate_demo_data():
        context = get_current_context()
        if not context["params"]["generate_new_data"]:
            return {"status": "existing_data", "new_sales": 0, "new_demand": 0}
        return call_api("/generate", {
            "request_id": context["run_id"],
            "sales_rows": context["params"]["sales_rows"]
        })

    @task
    def ingest_into_postgres(generation):
        return call_api("/ingest", {"require_postgres": True})["snapshot"]

    @task
    def validate_transform_and_load(snapshot):
        result = call_api("/load", {"snapshot": snapshot})
        return {"batch": result["batch"], "counts": result["table_counts"]}

    @task
    def execute_three_questions(load_result):
        return call_api("/queries", {})

    generated = generate_demo_data()
    snapshot = ingest_into_postgres(generated)
    loaded = validate_transform_and_load(snapshot)
    execute_three_questions(loaded)


refresh_pipeline()
