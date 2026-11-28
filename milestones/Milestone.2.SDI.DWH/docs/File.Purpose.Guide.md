# Milestone 2 File Purpose Guide

This guide explains the important Milestone 2 files in simple words.

## Dashboard and pipeline

| File | Purpose |
| --- | --- |
| `bi_dashboard/Milestone.2.SDI.BI.Excel.pbix` | Power BI Desktop business dashboard. Although “Excel” appears in the filename, `.pbix` is a Power BI report. |
| `airflow_dags/sdi_dashboard_refresh_dag.py` | Defines the `sales_demand_visuals` Airflow DAG. It has four tasks: optionally generate a new month, load PostgreSQL staging, validate and load DuckDB, then run the three SQL questions. |
| `code/start_dashboard_pipeline_api.py` | Starts the Windows API that Airflow calls for optional demo-data generation and the ingestion, loading, and query steps. |
| `docs/Automated.Refresh.Guide.md` | Shows how to start the API, copy the DAG into Airflow, run a refresh, and then update Power BI. |

After Airflow completes, refresh Power BI separately in Power BI Desktop using **Home → Refresh**.

## Report and video

| File | Purpose |
| --- | --- |
| `Milestone.2.SDI.BI.Report.pdf` | Five-page report explaining the BI problem, dashboard pages and charts, refresh process, results, and an implementation issue and fix. |
| `README.md` | Short overview of what this milestone contains and where to find instructions. |
| `video/Milestone.2.SDI.DWH.Video.mp4` | Recorded Milestone 2 demonstration. |

## Refresh evidence

| File or folder | What it shows |
| --- | --- |
| `Refresh.Results.And.Screenshots/M2.DuckDB.Counts.After.Two.Refreshes.png` | Original terminal screenshot of DuckDB record counts after refresh 1 and refresh 2. |
| `Refresh.Results.And.Screenshots/Milestone.2.SDI.DWH.Refresh.Counts.csv` | Starting and prepared monthly-batch totals: 500,000 sales / 27,216 demand, then 501,000 / 27,972, then 502,000 / 28,728. These are preparation counts; the later two Airflow refresh counts are in the M2 report and terminal screenshot. |
| `Refresh.Results.And.Screenshots/Refresh.1.Sales.501000.png` and `Refresh.2.Sales.502000.png` | Generator screenshots showing the two synthetic monthly data batches being prepared. |
| `Refresh.Results.And.Screenshots/Dashboard.2025.Historical.View.png` | Saved dashboard view with 2025 selected. Choose 2026 in Power BI to inspect later months. |
| `Refresh.Results.And.Screenshots/archive/Previous.Five.Task.Run.png` | Older Airflow screenshot from before the current four-task workflow. It is kept for reference and does not represent the current DAG. |
| `Refresh.Results.And.Screenshots/README.md` | Explains the refresh evidence files. |

## Refresh story in simple numbers

Before the two Airflow refreshes, the warehouse had 502,000 sales rows and 28,728 hospital-demand rows. Refresh 1 added 1,000 sales rows and 756 demand rows, bringing totals to 503,000 and 29,484. Refresh 2 added another monthly batch, bringing totals to 504,000 and 30,240. Earlier records stay in the warehouse.

The SQL answer CSVs and other runtime data are under `Project.Data.And.Results/results/` at the project root, outside this milestone folder.
