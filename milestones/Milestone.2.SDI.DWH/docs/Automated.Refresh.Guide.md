# Run the Milestone 2 refresh

The `sales_demand_visuals` DAG has four tasks: optional new-month generation, PostgreSQL staging ingestion, validation and DuckDB loading, and execution of the three SQL questions. After the DAG succeeds, refresh the Power BI report separately in Power BI Desktop.

## 1. Start the Windows API

In Windows PowerShell at the project root, start the API and leave it running. Use the current Windows gateway address for your WSL setup; this example uses `172.17.128.1`.

```powershell
.\.venv\Scripts\python.exe .\milestones\Milestone.2.SDI.DWH\code\start_dashboard_pipeline_api.py --host 172.17.128.1 --port 8765
```

## 2. Copy the current DAG into Airflow

In a second Windows PowerShell window, copy the M2 DAG into the Airflow filename already used for this DAG.

```powershell
wsl -d Ubuntu --exec cp "/mnt/d/IDA'26/Project Phase 1/milestones/Milestone.2.SDI.DWH/airflow_dags/sdi_dashboard_refresh_dag.py" /home/p/airflow/dags/sales_demand_visuals.py
```

Keep Airflow running. Open `http://localhost:8080`, refresh the page, and open `sales_demand_visuals`.

## 3. Run a new-data refresh

Trigger the DAG. To add a new month, turn on **Generate the next month**, leave **New sales rows** at `1000`, and confirm. Wait until all four tasks are successful. Leave generation off for a rerun that should only load the existing source files.

The starting totals for the two recorded refreshes were 502,000 sales rows and 28,728 hospital-demand rows. Refresh 1 brought them to 503,000 and 29,484. Refresh 2 brought them to 504,000 and 30,240. Each monthly batch adds 1,000 sales rows and 756 demand rows (12 hospitals × 63 medicines).

Each Airflow run ID is saved with its generated batch. Retrying the same run reuses that batch and avoids creating duplicate rows.

## 4. Refresh Power BI

After the Airflow tasks finish, open `milestones/Milestone.2.SDI.DWH/bi_dashboard/Milestone.2.SDI.BI.Excel.pbix` in Power BI Desktop and select **Home → Refresh**. Select 2026 in the Year filter to inspect the newly added months. Power BI Desktop refresh is a separate manual step from the Airflow DAG.

The M2 workflow ends at the SQL query layer. Refresh the Power BI report in Desktop afterward.
