# Phase 1 without Docker

Prepared for Hiba and Bilqees. This code follows the final Activity 4 workbook.

## What this first code package does

It reads the medicine master, pharmacy sales and hospital demand CSV files. It checks the data, builds seven dimensions and two facts in DuckDB, and runs your three SQL questions. The results are saved as CSV files that you can open in Excel. It keeps old facts. Running the same source records again does not add them twice.

No Docker is needed. Your planning Excel file is not edited. Do not import the planning descriptions as actual transaction records.

## Start with this in VS Code

1. Extract the ZIP. Open the **Phase1.NoDocker** folder in VS Code.
2. Open **Terminal > New Terminal**. Use a Python version supported by the packages. The tested version is Python 3.12.
3. Create your own environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

4. Copy the settings example:

```powershell
Copy-Item config.example.json config.json
```

5. Open `config.json`. Check `source_folder`. It must be the folder that directly contains the three CSV files. Forward slashes are accepted on Windows. Leave `postgres_dsn` empty for the first practice run.
6. Run:

```powershell
.\.venv\Scripts\python.exe run_pipeline.py
```

The first full run can take a few minutes. It reads 500,000 sales records. Wait for the summary. An error means the run did not complete; do not treat a partly created folder as a successful load.

## What to open after a successful run

* `results/validation.json`: table counts, missing links and the eight known location conflicts.
* `results/01_sales_by_medicine_month_channel_city.csv`: Question 1 answers.
* `results/02_hospital_forecast_consumption.csv`: Question 2 answers.
* `results/03_sales_and_demand_side_by_side.csv`: Question 3 answers.
* `results/query_metrics.json`: query duration and result row counts.
* `results/run_summary.json`: the completed run summary.
* `data/sales_demand.duckdb`: the actual analytical database.

Dimension counts include one extra Unknown row with key 0. For example, 63 medicines become 64 dimension rows. The fact counts should stay 500,000 and 27,216 for the original source files.

To show that rerunning does not create duplicates, run the same command again and compare the fact counts. To run only the queries:

```powershell
.\.venv\Scripts\python.exe run_pipeline.py --queries-only
```

You can open the result CSVs in Excel for screenshots. The SQL files in `sql` are editable. This package does not require VS Code database extensions.

## The Python files in easy words

| File | Job |
|---|---|
| settings.py | Reads your folder and database settings. |
| ingest.py | Copies a stable snapshot and can load it into PostgreSQL staging. |
| model.py | Checks the records, prepares fields and loads the dimensions and facts. |
| run_pipeline.py | Runs the steps and saves SQL answers. |
| api.py | Provides local HTTP endpoints for the pipeline steps. |
| watch_files.py | Watches for file changes and asks Airflow to run. |
| airflow_dags/pharma_phase1.py | Makes Airflow run ingestion, transformation and queries in order. |
| table_fields.json | Lists the actual table fields and their database types. |
| tests/test_pipeline.py | Checks duplicate prevention, rollback and dated dimension changes. |

## PostgreSQL staging without Docker

The project guideline requires PostgreSQL staging. Local practice mode is useful for learning, but does not meet that requirement by itself.

PostgreSQL 18 was found on this computer. The connection requested a password, so its data connection has not been tested. Do not reinstall it just because the first practice run uses DuckDB.

In pgAdmin, create a database named `pharma_project` using your own login. In `config.json`, set `postgres_dsn` to a connection string like this, replacing the example password:

```text
host=localhost port=5432 dbname=pharma_project user=postgres password=YOUR_PASSWORD
```

Do not post your real password in chat or commit `config.json` to GitHub. The `.gitignore` excludes that file. You can also supply the connection string through `PHARMA_POSTGRES_DSN` in your own terminal.

Run:

```powershell
.\.venv\Scripts\python.exe run_pipeline.py --require-postgres
```

This creates `pharma_staging.raw_master`, `raw_sales`, `raw_demand` and `batch_log`. It replaces only the staging snapshot, then reads the staged export to build the mart. It never empties the historical fact tables. PostgreSQL must be running, and your user must be allowed to create the staging schema and its tables.

## Local API

In a terminal, run:

```powershell
.\.venv\Scripts\python.exe api.py
```

Open `http://127.0.0.1:8000/health`. Keep this terminal running.

For local file watching practice, open another terminal:

```powershell
.\.venv\Scripts\python.exe watch_files.py --practice
```

Practice mode calls the Python pipeline directly. It is not the final Airflow demonstration. The first watcher check causes an initial run. Further runs happen only when source contents change and file sizes and modification times are stable. It does not invent new data or modify source files.

## Airflow without Docker

Airflow itself must run in Linux or WSL on Windows. Do not install it into the native Windows environment above. Use a separate WSL environment and the official installation instructions for a chosen Airflow 3 version. Keep its constraints file matched to its Python version.

Copy `airflow_dags/pharma_phase1.py` into your Airflow DAGs folder. The DAG uses `airflow.sdk` from Airflow 3. Set `PHARMA_API_URL` in WSL to the Windows API address. With WSL mirrored networking, localhost can be used. Test `/health` from WSL before running the DAG. Other WSL networking setups need deliberate networking configuration; this package does not change your firewall or WSL settings.

The DAG has three visible tasks:

1. Ingest into PostgreSQL through the API.
2. Validate, transform and load the mart.
3. Run the three SQL questions.

The DAG requires real PostgreSQL staging. It refuses to use practice staging. It allows only one active DAG run and retries a failed task once.

The watcher can trigger the DAG through Airflow 3 REST API. Set `AIRFLOW_API_URL` and a valid `AIRFLOW_API_TOKEN` in the watcher terminal, then run `python watch_files.py` without `--practice`. Obtain the token using the authentication method configured in your own Airflow installation. Airflow must already be running and the DAG must be unpaused. Scheduling through Airflow is prepared in this package but has not been executed here.

## Important rules already implemented

Medicine GTIN and GLN codes stay as text. Source IDs are checked for duplicates. Bad data rolls back the mart transaction. Seven dimensions and two facts use the field names from the final workbook. AverageOccupancyRatePct is in DimHospital for the supplied fixed hospital values. Region is omitted because no agreed lookup exists.

PackSizeBand uses the proposed cutoff 15. BedSizeBand uses the proposed cutoffs 300 and 600. These are project assumptions. The source numbers remain available.

Medicine prices, selected classifications, pharmacy type and location, and hospital capacity or location use Type 2 versions when changed. The first run establishes the baseline. No missing past history is invented. Set `change_effective_date` only when there is a real dated change. A new version closes the old half open interval: the start date is included and the end date is excluded.

Existing source events are treated as immutable. If an already loaded transaction is edited, the code stops for review. It does not silently overwrite history. Brand new IDs append new facts. The original source snapshot is expected to contain consistent entity descriptions. Conflicting descriptions for one entity in the same snapshot stop the run.

Missing medicine IDs and invalid dates stop validation. Key 0 exists for unresolved date valid lookups; counts of such fact rows are recorded for review. The mart checks all 11 diagram relationships explicitly. These checks do not depend on DuckDB enforcing foreign key constraints.

The two facts are never joined directly at transaction level. Query 3 groups them separately before comparing hospital, medicine and month. It does not add sales to consumption. Its outer join keeps missing comparisons blank rather than pretending no record means zero.

## What still belongs to the wider project

This is the first implementation package through SQL answers. BI dashboards, their automated refresh demonstration, the seven file synthetic generator, its 1 to 2 page PDF, monitoring dashboards, and Phase 2 and Phase 3 marts are not claimed as complete. A repeat run with unchanged data proves duplicate prevention, not the required two refreshes with new generated data.

Keep the existing Excel workbook as your design. Keep Python, SQL, screenshots and the updated report beside it in GitHub. The report must describe what you actually ran.

## Technical references

* Airflow Windows and WSL requirements: https://airflow.apache.org/docs/apache-airflow/stable/installation/prerequisites.html
* Airflow 3 standalone setup: https://airflow.apache.org/docs/apache-airflow/3.1.0/start.html
* DuckDB CSV reader: https://duckdb.org/docs/stable/data/csv/overview
* Psycopg PostgreSQL COPY: https://www.psycopg.org/psycopg3/docs/basic/copy.html
