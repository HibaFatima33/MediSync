# MediSync: Phase 1, Milestone 1

## Sales and Demand Intelligence Data Warehouse

| Group member | ERP |
| --- | --- |
| Hiba Fatima | 29005 |
| Bilqees Nazar | 31638 |

## Problem we are solving

Medicine sales and hospital demand are stored in separate files. Sales record individual transactions, while hospital demand records one hospital, medicine and month. This makes them difficult to compare directly.

We prepare these records in one reporting model so we can study medicine sales, hospital forecasts, actual consumption and unmet demand.

## What we implemented

Our Milestone 1 work covers the data warehouse through the SQL query layer.

1. Read the medicine master, pharmacy sales and hospital demand CSV files.
2. Load the incoming records into PostgreSQL staging.
3. Use Python to check IDs, dates, prices and other data rules.
4. Prepare seven dimension tables and two fact tables in DuckDB.
5. Run three SQL questions and save their answers as CSV files.
6. Use Airflow to run ingestion, transformation and queries in order.
7. Use Power BI to show data engineering measurements.

The flow is:

```text
Source CSV files
    -> PostgreSQL staging
    -> Python validation and transformation
    -> DuckDB dimensions and facts
    -> SQL answer CSV files
```

Airflow controls the order of the tasks. PostgreSQL staging holds the incoming source snapshot. DuckDB holds the prepared reporting tables.

## Reporting model

We use two fact tables:

- **FactPharmacySales:** one row for each sales transaction.
- **FactHospitalDemand:** one row for each hospital, medicine and month.

Seven dimensions describe Medicine, Pharmacy, Hospital, Location, Sales Profile, Demand Status and Date. The fact tables share Medicine and Date dimensions.

We group sales by hospital, medicine and month before comparing them with monthly hospital demand. We do not join individual sales directly to monthly demand records, because that could repeat the demand totals.

## Our three SQL questions

1. How do medicine sales change by month, sales channel and city?
2. How does hospital forecast demand compare with actual consumption and unmet demand?
3. How do hospital pharmacy sales compare with hospital demand for the same medicine and month?

The SQL files are in `milestones/Milestone.1.SDI.DWH/sql/`.

## Airflow implementation

The Milestone 1 DAG is named `pharma_phase1`. It has three tasks:

```text
 ingest_into_postgres
          -> validate_transform_and_load
          -> execute_three_questions
```

Airflow runs in Ubuntu through WSL. A Windows API runs the local Python steps when Airflow requests them. This project runs without Docker.

## Oversampled data

The submitted snapshot contains:

| Source | Original records | Submitted records |
| --- | ---: | ---: |
| Medicine master | 63 | 63 |
| Pharmacy sales | 500,000 | 502,000 |
| Hospital demand | 27,216 | 28,728 |

We created sample records for January and February 2026 using existing record templates, new IDs and new dates. Each batch adds 1,000 sales and 756 hospital demand records. These are synthetic demonstration records, not newly collected real business records. Earlier records are retained.

The `oversampled_data` folder contains the submitted data, generation notes and a dictionary explaining all 120 source columns. Sales are split into CSV parts for GitHub. The restore script joins these parts and checks the supplied files. The folder structure separates the complete source snapshot, generated demo rows for inspection, and refresh history. The generated demo rows are already included in the complete snapshot and must not be added again. See `oversampled_data/README.md` for the folder map and restore instructions.

## Data engineering dashboard

The Power BI file is in `Pipeline.Monitoring (Power BI)/`.

It shows:

- Source records processed.
- Records in dimension and fact tables.
- PostgreSQL staging load time.
- SQL query execution time.
- Database storage size and available date coverage.

Run `export_pipeline_monitoring.py` to export the measurements, then refresh Power BI manually. These charts describe pipeline performance and data size.

## Submission files

```text
Project Phase 1/
  README.md
  RUNNING_COMMANDS.md
  Pipeline.Monitoring (Power BI)/
    MediSync.Pipeline.Monitoring.pbix
  milestones/
    Milestone.1.SDI.DWH/
      code/
      config/
      airflow_dags/
      sql/
      tests/
      docs/
      Results.And.Screenshots/
      oversampled_data/
      video/
      requirements.txt
      Milestone.1.SDI.DWH.Report.pdf
      Milestone.1.SDI.DWH.Excel.xlsx
      Milestone.1.SDI.DWH.GitHub.txt
  Project.Data.And.Results/    Local data and outputs; ignored by Git
```

The report is a maximum of five pages. It explains our design, Airflow pipeline, implementation problems and solutions, data engineering dashboards, and oversampling assumptions. It also includes supporting screenshots of additional work already completed.

**Video status:** The Milestone 1 demo video will be uploaded shortly as `Milestone.1.SDI.DWH.Video.mp4` in the `video` folder. The recording must be no longer than five minutes.

## First setup

Open Windows PowerShell in the project root. Install Python and PostgreSQL before starting. Airflow uses a separate Ubuntu WSL environment.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\milestones\Milestone.1.SDI.DWH\requirements.txt
.\.venv\Scripts\python.exe .\milestones\Milestone.1.SDI.DWH\code\restore_oversampled_data.py
Copy-Item .\milestones\Milestone.1.SDI.DWH\config\config.example.json .\milestones\Milestone.1.SDI.DWH\config\config.json
```

The setup commands are for a fresh clone. If `config.json` already exists, keep your current settings instead of replacing it. Enter your private PostgreSQL connection in that file. Do not upload passwords or private configuration to GitHub.

Local inputs and the DuckDB database are stored in `Project.Data.And.Results/data/`. Current SQL answers and monitoring exports are stored in `Project.Data.And.Results/results/`.

The Milestone 1 API is `milestones/Milestone.1.SDI.DWH/code/start_query_layer_api.py`. Its connection address must match the `PHARMA_API_URL` used by Airflow. See the running guide for the environment setup; its dashboard commands are additional work outside this Milestone 1 summary.

For file descriptions, see `milestones/Milestone.1.SDI.DWH/docs/File.Purpose.Guide.md`.

