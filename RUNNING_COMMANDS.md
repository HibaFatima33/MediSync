# Phase 1 Running Commands

Use **Windows PowerShell** from the project root. Keep PostgreSQL running.

```powershell
cd "D:\IDA'26\Project Phase 1"
```

## M1: Run the DWH through the SQL query layer

### 1. Start the M1 API

Open a PowerShell terminal and leave this running:

```powershell
.\.venv\Scripts\python.exe .\milestones\Milestone.1.SDI.DWH\code\start_query_layer_api.py --host 0.0.0.0 --port 8765
```

### 2. Start Airflow in Ubuntu

Open a second PowerShell terminal and enter Ubuntu:

```powershell
wsl -d Ubuntu
```

At the Ubuntu prompt, start Airflow:

```bash
source /home/p/pharma-airflow/.venv/bin/activate
export AIRFLOW_HOME=/home/p/airflow
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export PHARMA_API_URL=http://172.17.128.1:8765
airflow standalone
```

If `172.17.128.1` is not the current Windows gateway, check it from Ubuntu:

```bash
ip route show default
```

Use the gateway address shown after `via` in `PHARMA_API_URL` and in the API’s `--host` value.

Open Airflow at [http://localhost:8080](http://localhost:8080). Find and trigger **`pharma_phase1`**. The M1 DAG has three tasks: ingest source data into PostgreSQL, validate/transform/load the warehouse, and run the three SQL questions.

### 3. Show the M1 SQL results

After the Airflow run succeeds, open the results folder:

```powershell
Start-Process .\Project.Data.And.Results\results
```

The three SQL result files answer questions about monthly medicine sales, hospital forecast versus consumption, and sales compared with demand.

### 4. Run the M1 pipeline directly, if needed

Use this only while Airflow is idle:

```powershell
.\.venv\Scripts\python.exe .\milestones\Milestone.1.SDI.DWH\code\run_dwh_pipeline.py --require-postgres
```

To rerun only the SQL questions:

```powershell
.\.venv\Scripts\python.exe .\milestones\Milestone.1.SDI.DWH\code\run_dwh_pipeline.py --queries-only
```

## M2: Demonstrate the BI dashboard and two refreshes

M2 uses the SDI warehouse and adds a Power BI business dashboard. Run the pipeline twice, then refresh Power BI after each completed run.

### 1. Start the M2 API

Open a PowerShell terminal and leave it running:

```powershell
.\.venv\Scripts\python.exe .\milestones\Milestone.2.SDI.DWH\code\start_dashboard_pipeline_api.py --host 0.0.0.0 --port 8765
```

If you use a different Windows gateway address, replace `0.0.0.0` with the address Airflow can reach, and set the matching URL in Airflow’s `PHARMA_API_URL`.

### 2. Start Airflow in Ubuntu

Open a second PowerShell terminal:

```powershell
wsl -d Ubuntu
```

At the Ubuntu prompt:

```bash
source /home/p/pharma-airflow/.venv/bin/activate
export AIRFLOW_HOME=/home/p/airflow
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export PHARMA_API_URL=http://172.17.128.1:8765
airflow standalone
```

Open [http://localhost:8080](http://localhost:8080). Find the **`sales_demand_visuals`** DAG and trigger it.

For a refresh that adds a new demo month, turn on **Generate the next month** in the Airflow trigger form. Leave it off when you want to reload the current source files without generating new records.

The current M2 DAG has four tasks:

1. **Generate demo data** — creates another demo batch when the option is enabled; otherwise, it skips generation.
2. **Ingest into PostgreSQL** — loads a snapshot of the source files into staging.
3. **Validate, transform and load** — checks and prepares the data, then updates the DuckDB reporting tables.
4. **Execute three questions** — runs the SQL queries that Power BI reads.

Wait until all four tasks show success before continuing.

### 3. Check the refreshed warehouse counts

In a separate PowerShell terminal, run:

```powershell
.\.venv\Scripts\python.exe -X utf8 -c "import duckdb; c=duckdb.connect('Project.Data.And.Results/data/sales_demand.duckdb', read_only=True); c.sql('SELECT COUNT(*) AS SalesRecords FROM FactPharmacySales').show(); c.sql('SELECT COUNT(*) AS DemandRecords FROM FactHospitalDemand').show(); c.close()"
```

The refresh evidence you shared shows these counts:

| Checkpoint | Sales records | Hospital demand records |
|---|---:|---:|
| Before the demo refreshes | 502,000 | 28,728 |
| After refresh 1 | 503,000 | 29,484 |
| After refresh 2 | 504,000 | 30,240 |

Use the counts actually shown by your current DuckDB database when recording. Each refresh added 1,000 sales records and 756 demand records in the saved demo evidence.

### 4. Refresh Power BI after each Airflow run

Open the M2 Power BI file:

```powershell
Start-Process .\milestones\Milestone.2.SDI.DWH\bi_dashboard\Milestone.2.SDI.BI.Excel.pbix
```

In Power BI Desktop, choose **Home → Refresh**. Show the new period or changed values. Repeat after the second successful Airflow run.

The dashboard pages are:

- **Sales:** net sales, gross profit, packs sold, gross margin, monthly sales, sales by channel, top medicines and a drill-down table.
- **Hospital Demand:** forecast packs, consumed packs, unmet demand, monthly forecast versus actual, unmet demand by hospital and a detail table.
- **Sales Vs Demand:** hospital pharmacy sales beside hospital consumption, their comparison percentage, hospital comparisons and details. Sales and consumption are separate measures, so the page compares them rather than adding them together.

### 5. Show M2 refresh evidence

In Airflow, show the successful `sales_demand_visuals` run and its four tasks. Show the DuckDB counts, then show Power BI after **Home → Refresh**. Repeat for the second run.

The saved report contains a screenshot of a five-task run from the recorded demonstration. Your current DAG has four tasks; explain the four current stages if you show a fresh run.

## M1 pipeline-monitoring Power BI

This is a separate technical monitoring dashboard, not the M2 business dashboard.

Export the monitoring files:

```powershell
.\.venv\Scripts\python.exe .\milestones\Milestone.1.SDI.DWH\code\export_pipeline_monitoring.py
```

Open the monitoring PBIX:

```powershell
Start-Process ".\Pipeline.Monitoring (Power BI)\MediSync.Pipeline.Monitoring.pbix"
```

It shows pipeline measurements such as rows processed, staging load time, reporting-table counts, SQL query time, and database storage. If the PBIX cannot find its monitoring CSVs, update its data sources in Power BI using **Transform data → Data source settings**, then refresh.

## M1 file watcher demonstration

The watcher detects a changed source file and asks Airflow to run. Keep the API and Airflow running, and make sure no pipeline run is active.

In a Windows PowerShell terminal:

```powershell
wsl -d Ubuntu --exec /home/p/pharma-airflow/.venv/bin/python "/mnt/d/IDA'26/Project Phase 1/milestones/Milestone.1.SDI.DWH/code/watch_csv_and_trigger_airflow.py" --config "/mnt/d/IDA'26/Project Phase 1/milestones/Milestone.1.SDI.DWH/config/config.json" --once
```

In another PowerShell terminal, update the sales source file’s modified time to demonstrate a file change:

```powershell
$cfg = Get-Content .\milestones\Milestone.1.SDI.DWH\config\config.json -Raw | ConvertFrom-Json
$source = $cfg.source_folder
if (-not [System.IO.Path]::IsPathRooted($source)) { $source = Join-Path (Get-Location) $source }
$sales = Get-Item -LiteralPath (Join-Path $source "05_pharmacy_sales_data.csv")
$sales.LastWriteTime = [datetime]::Now
```

Show whether the watcher accepted the change and whether Airflow completed the resulting run.

## Stop the services

Wait for any active run to finish. Press **Ctrl+C** in the API and Airflow terminals when you are done. If the watcher is running continuously, stop it with **Ctrl+C** too.
