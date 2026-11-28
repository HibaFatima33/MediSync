# MediSync — Sales and Demand Intelligence

MediSync combines medicine sales and hospital demand data for reporting. The project uses Python, PostgreSQL, DuckDB, SQL, Apache Airflow and Power BI.

## Group Members

| Name | ERP |
| --- | --- |
| Hiba Fatima | 29005 |
| Bilqees Nazar | 31638 |

## Phase 1: Sales and Demand Intelligence

### Milestone 1: Data Warehouse and SQL

Milestone 1 builds the reporting warehouse through the SQL query layer.

- PostgreSQL stores incoming records in staging.
- Python validates and prepares the data.
- DuckDB stores seven dimensions and two fact tables.
- Three SQL queries answer sales and hospital-demand questions.
- The `pharma_phase1` Airflow DAG runs ingestion, warehouse loading and the SQL queries.
- A Power BI monitoring report shows pipeline measurements.
- The submission includes the prepared data snapshot and its data dictionary.

See the [Milestone 1 folder](milestones/Milestone.1.SDI.DWH/) for the report, Excel workbook, code, data and evidence.

**Milestone 1 video:** [Watch the recording](milestones/Milestone.1.SDI.DWH/video/Milestone.1.SDI.DWH.Video.mp4).

### Milestone 2: Business Intelligence and Refreshing

Milestone 2 adds a Power BI business dashboard with Sales, Hospital Demand and Sales Vs Demand pages. Filters and detail tables help users investigate changes in sales and hospital demand.

The `sales_demand_visuals` Airflow DAG runs four tasks: optional demo-data generation, PostgreSQL ingestion, validation and DuckDB loading, and the three SQL queries. After the DAG succeeds, refresh the Power BI report separately in Power BI Desktop using **Home → Refresh**.

The two demonstrated refreshes increased the DuckDB totals from 502,000 sales and 28,728 demand rows to 503,000 and 29,484, then to 504,000 and 30,240.

See the [Milestone 2 folder](milestones/Milestone.2.SDI.DWH/) for the report, Power BI file, Airflow code, refresh evidence and video.

**Milestone 2 video:** [Watch the recording](milestones/Milestone.2.SDI.DWH/video/Milestone.2.SDI.DWH.Video.mp4).

## Run the Project

See [RUNNING_COMMANDS.md](RUNNING_COMMANDS.md) for setup and execution instructions.
