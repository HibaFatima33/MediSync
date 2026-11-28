# Milestone 1 File Purpose Guide

This guide explains what each important M1 file contains and what it is used for.

## Main code and design files

| File | Purpose |
| --- | --- |
| `code/project_settings.py` | Read the settings and find the project folders. |
| `code/load_csv_to_postgres.py` | Save a copy of incoming CSV files and load their records into PostgreSQL staging. |
| `code/build_duckdb_tables.py` | Check records, match dimension keys, and load dimension and fact tables into DuckDB. |
| `code/run_dwh_pipeline.py` | Run ingestion, transformation, loading, and the three SQL questions. |
| `code/start_query_layer_api.py` | Let Airflow request ingestion, loading, and SQL execution from Windows Python code. |
| `code/generate_demo_records.py` | Create sample monthly sales and demand records while keeping earlier records. |
| `code/export_pipeline_monitoring.py` | Export counts, loading times, query times, date coverage, and storage sizes for Power BI. |
| `code/monitoring_events.py` | Record ingestion and query outcomes for pipeline monitoring. |
| `code/watch_csv_and_trigger_airflow.py` | Optional helper that checks for source CSV changes and requests an Airflow run. |
| `code/restore_oversampled_data.py` | Join the submitted sales CSV parts, verify them, and rebuild the three local source CSVs. |
| `config/config.example.json` | Give example folder paths and database settings without a private password. |
| `config/reporting_table_fields.json` | List reporting table columns and their data types. |
| `requirements.txt` | List Python packages needed to run the code. |
| `airflow_dags/sdi_query_layer_dag.py` | Define the `pharma_phase1` Airflow workflow: ingestion, transformation/loading, then SQL queries. |
| `sql/01_sales_by_medicine_month_channel_city.sql` | Summarize medicine sales by month, channel, and city. |
| `sql/02_hospital_forecast_consumption.sql` | Compare hospital forecasts with actual consumption and show unmet demand. |
| `sql/03_sales_and_demand_side_by_side.sql` | Compare hospital pharmacy sales and hospital demand for the same medicine and month. |

## Oversampled data folder

In this project, **oversampled** means we added synthetic demo records to the original data to provide January and February 2026 for monthly analysis and refresh demonstrations. This is a time extension of the sample data, not a statistical method for balancing categories. The new rows use existing records as templates with new IDs and dates. The complete snapshot keeps all original records.

| File or folder | What it contains / how to use it |
| --- | --- |
| `oversampled_data/README.md` | Explains the added records, row counts, folder layout, and restore command. |
| `oversampled_data/Milestone.1.SDI.DWH.Data.Dictionary.csv` | Explains source CSV columns: meaning, type, unit, example, and generation rule. |
| `oversampled_data/manifest.json` | Lists complete snapshot files and sales-part order, expected row counts, and SHA-256 checksums used by the restore script. |
| `oversampled_data/complete_snapshot/01_master_data.csv` | Complete medicine master: 63 medicine records; no demo rows were added. |
| `oversampled_data/complete_snapshot/06_hospital_demand_data.csv` | Complete demand source: 28,728 rows, including 1,512 added demo rows. Each row represents a hospital, medicine, and month. |
| `oversampled_data/complete_snapshot/sales_parts/part-001.csv` to `part-011.csv` | The complete pharmacy sales source split into 11 ordered pieces: 502,000 rows total, including 2,000 added demo rows. The split keeps each file small enough for GitHub. |
| `oversampled_data/generated_demo_rows/05_pharmacy_sales_data.csv` | Copy of only the 2,000 generated sales rows, provided for inspection. They are already inside the complete sales snapshot. |
| `oversampled_data/generated_demo_rows/06_hospital_demand_data.csv` | Copy of only the 1,512 generated demand rows, provided for inspection. They are already inside the complete demand snapshot. |
| `oversampled_data/refresh_history/demo_state.json` | Records which demo refreshes are marked complete in the submitted example. |
| `oversampled_data/refresh_history/refresh_1_method.json` and `refresh_2_method.json` | Describe the generation assumptions for the two submitted demo batches. |

**Important:** Do not append the CSVs in `generated_demo_rows` to the complete snapshot. They are inspection copies; appending them would duplicate the demo records. The 11 sales parts are the pieces to join to restore the complete sales source file.
