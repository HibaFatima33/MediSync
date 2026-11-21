# Phase 1 running commands

Use Windows PowerShell in the project root. Keep PostgreSQL running. The existing local folder is D:/IDA'26/Project Phase 1.

```powershell
cd "D:\IDA'26\Project Phase 1"
```

## API and Airflow

In PowerShell enter Ubuntu, then find the Windows gateway inside Ubuntu.

```powershell
wsl -d Ubuntu
```

```bash
ip route show default | awk '{print $3}'
```

The previous address was 172.17.128.1. Replace it below if yours differs. In a separate Windows PowerShell tab start the current API.
172.17.128.1
```powershell
.\.venv\Scripts\python.exe .\milestones\Milestone.2.SDI.DWH\code\start_dashboard_pipeline_api.py --host 172.17.128.1 --port 8765
```

Keep it open. In Ubuntu run the health check and start your existing Airflow environment.

```bash
curl --max-time 10 http://172.17.128.1:8765/health
then this 


source /home/p/pharma-airflow/.venv/bin/activate
export AIRFLOW_HOME=/home/p/airflow
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export PHARMA_API_URL=http://172.17.128.1:8765
airflow standalone
```

Open http://localhost:8080 and sign in. The DAG ID remains sales_demand_visuals so the same run history is available. Its source file now lives in Milestone 2. Copy it to the existing Airflow filename when needed, using a separate PowerShell tab.

```powershell
wsl -d Ubuntu --exec mkdir -p /home/p/airflow/dags
wsl -d Ubuntu --exec cp "/mnt/d/IDA'26/Project Phase 1/milestones/Milestone.2.SDI.DWH/airflow_dags/sdi_dashboard_refresh_dag.py" /home/p/airflow/dags/sales_demand_visuals.py
```

The three task milestone DAG has ID pharma_phase1. To update that existing workflow use its Milestone 1 file.

```powershell
wsl -d Ubuntu --exec cp "/mnt/d/IDA'26/Project Phase 1/milestones/Milestone.1.SDI.DWH/airflow_dags/sdi_query_layer_dag.py" /home/p/airflow/dags/pharma_phase1.py
```

For the full demo, unpause sales_demand_visuals and Trigger once. For new data turn on Generate the next month in the Trigger form. Wait for five green tasks. The three task milestone workflow covers ingestion, loading and SQL. The full workflow includes optional next-month generation and dashboard generation. See milestones/Milestone.2.SDI.DWH/docs/Automated.Refresh.Guide.md.

## Dashboard and SQL answers

After a successful run use Windows PowerShell.

```powershell
Start-Process .\Project.Data.And.Results\results
Start-Process .\Project.Data.And.Results\results\dashboard.html
```

For a manual dashboard rebuild after a direct query run use the Milestone 2 builder.

```powershell
.\.venv\Scripts\python.exe .\milestones\Milestone.2.SDI.DWH\code\build_business_dashboard.py
```

## Direct DWH run and SQL questions

Run these only while Airflow is idle. A direct DWH run loads sources and creates query answers. Rebuild the dashboard separately if needed.

```powershell
.\.venv\Scripts\python.exe .\milestones\Milestone.1.SDI.DWH\code\run_dwh_pipeline.py --require-postgres
.\.venv\Scripts\python.exe .\milestones\Milestone.1.SDI.DWH\code\run_dwh_pipeline.py --queries-only
```

## Fact counts

```powershell
.\.venv\Scripts\python.exe -X utf8 -c "import duckdb; c=duckdb.connect('Project.Data.And.Results/data/sales_demand.duckdb', read_only=True); c.sql('SELECT COUNT(*) AS SalesRecords FROM FactPharmacySales').show(); c.sql('SELECT COUNT(*) AS DemandRecords FROM FactHospitalDemand').show()"
```

The final counts from the two completed batches are 502000 sales and 28728 demand records.

## Monitoring

```powershell
.\.venv\Scripts\python.exe .\milestones\Milestone.1.SDI.DWH\code\export_pipeline_monitoring.py
Start-Process ".\Pipeline.Monitoring (Power BI)\MediSync.Pipeline.Monitoring.pbix"
```

Power BI data sources now point to Project.Data.And.Results/results/monitoring. If the saved PBIX still points to its old location, use Transform data, Data source settings, Change Source for each of the five CSVs, then Refresh and save.

## Watcher

Keep the API and Airflow running and wait for any active load to finish. In Windows PowerShell terminal A start the WSL watcher using the moved config.

```powershell
wsl -d Ubuntu --exec /home/p/pharma-airflow/.venv/bin/python "/mnt/d/IDA'26/Project Phase 1/milestones/Milestone.1.SDI.DWH/code/watch_csv_and_trigger_airflow.py" --config "/mnt/d/IDA'26/Project Phase 1/milestones/Milestone.1.SDI.DWH/config/config.json" --once
```

After its waiting message, in PowerShell terminal B update only the sales file modification time.

```powershell
$cfg = Get-Content .\milestones\Milestone.1.SDI.DWH\config\config.json -Raw | ConvertFrom-Json
$source = $cfg.source_folder
if (-not [System.IO.Path]::IsPathRooted($source)) { $source = Join-Path (Get-Location) $source }
$sales = Get-Item -LiteralPath (Join-Path $source "05_pharmacy_sales_data.csv")
$sales.LastWriteTime = [datetime]::Now
```

The watcher should request the run. Show its accepted request and the successful tasks. This test leaves row counts at their existing values.

## Generator

The existing demo already includes both refreshes. These commands document how new batches were created from an original baseline in a separate practice setup.

```powershell
.\.venv\Scripts\python.exe .\milestones\Milestone.1.SDI.DWH\code\generate_demo_records.py --prepare
.\.venv\Scripts\python.exe .\milestones\Milestone.1.SDI.DWH\code\generate_demo_records.py --refresh 1
.\.venv\Scripts\python.exe .\milestones\Milestone.1.SDI.DWH\code\generate_demo_records.py --refresh 2
```

Run Airflow after each generated batch. Completed refresh numbers are skipped. To test the moved generator without changing data use --help.

## Checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s .\milestones\Milestone.1.SDI.DWH\tests -v
```

## Stop

Wait for the current run to finish. Use Ctrl+C in the API, watcher and Airflow terminals when finished.

## New automated generation

The DAG now has five tasks. Restart the API and copy the updated DAG before using /generate. In Trigger turn on Generate the next month to add the next batch. Leave it off for an unchanged-data or watcher run. March and April 2026 are the next two periods after the completed January and February batches. 