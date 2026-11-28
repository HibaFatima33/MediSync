# Phase 1 Milestone 2 — SDI Business Intelligence

Milestone 2 adds a Power BI business dashboard and demonstrates two data refreshes for the Sales and Demand Intelligence project. The dashboard helps review medicine sales, hospital forecasts, consumption, and recorded unmet demand.

## Included

- `Milestone.2.SDI.BI.Report.pdf` — five-page report describing the BI pages and refresh story.
- `bi_dashboard/Milestone.2.SDI.BI.Excel.pbix` — Power BI Desktop report.
- `airflow_dags/sdi_dashboard_refresh_dag.py` — four-task Airflow workflow, with optional monthly demo-data generation.
- `code/start_dashboard_pipeline_api.py` — Windows API used by Airflow for pipeline requests.
- `Refresh.Results.And.Screenshots/` — count results and supporting refresh evidence.
- `video/Milestone.2.SDI.DWH.Video.mp4` — recorded demonstration.

## Refresh behavior

The `sales_demand_visuals` DAG runs four tasks in order: optionally generate a new monthly batch, load PostgreSQL staging, validate and load DuckDB, and execute the three SQL questions. After the DAG succeeds, open the PBIX in Power BI Desktop and select **Home → Refresh** to update the business dashboard.

The recorded count story is: 502,000 sales / 28,728 demand before the two Airflow refreshes; 503,000 / 29,484 after refresh 1; and 504,000 / 30,240 after refresh 2.

## Run instructions

See [`docs/Automated.Refresh.Guide.md`](docs/Automated.Refresh.Guide.md) for run commands and Airflow steps. See [`docs/File.Purpose.Guide.md`](docs/File.Purpose.Guide.md) for each file’s purpose.
