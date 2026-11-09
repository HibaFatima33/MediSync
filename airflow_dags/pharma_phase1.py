"""Airflow 3 DAG. Run Airflow in WSL, not native Windows. No Docker.

The Windows API handles Windows file paths and the local PostgreSQL connection.
Set PHARMA_API_URL in WSL to the Windows API URL. WSL mirrored networking can
use localhost; otherwise forward the API through a deliberately configured host
connection. Keep the API local while practicing on Windows.
"""
import json
import os
import urllib.request
from datetime import datetime,timedelta,timezone
from airflow.sdk import dag,task


def call(endpoint,body):
    url=os.environ.get("PHARMA_API_URL","http://127.0.0.1:8000")+endpoint
    request=urllib.request.Request(url,json.dumps(body).encode(),{"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(request,timeout=1800) as response:
        return json.load(response)


@dag(dag_id="pharma_phase1",start_date=datetime(2026,1,1,tzinfo=timezone.utc),
     schedule=None,catchup=False,max_active_runs=1,
     default_args={"retries":1,"retry_delay":timedelta(minutes=1)},tags=["Hiba","Bilqees","Phase1"])
def pipeline():
    @task
    def ingest_into_postgres():
        return call("/ingest",{"require_postgres":True})["snapshot"]

    @task
    def validate_transform_and_load(snapshot):
        result=call("/load",{"snapshot":snapshot})
        return {"batch":result["batch"],"counts":result["table_counts"]}

    @task
    def execute_three_questions(loaded):
        return call("/queries",{})

    execute_three_questions(validate_transform_and_load(ingest_into_postgres()))


pipeline()
