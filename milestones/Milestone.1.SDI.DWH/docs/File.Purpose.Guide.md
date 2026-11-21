# Milestone 1 File Purpose Guide

| File | Purpose |
| --- | --- |
| `code/project_settings.py` | Read the settings and find the project folders. |
| `code/load_csv_to_postgres.py` | Save a copy of the incoming CSV files and load their records into PostgreSQL staging. |
| `code/build_duckdb_tables.py` | Check the records, match dimension keys and load the dimension and fact tables into DuckDB. |
| `code/run_dwh_pipeline.py` | Run data ingestion, transformation, loading and the three SQL questions. |
| `code/start_query_layer_api.py` | Allow Airflow to request ingestion, loading and SQL execution from the Windows Python code. |
| `code/generate_demo_records.py` | Create sample monthly sales and demand records while keeping earlier records. |
| `code/export_pipeline_monitoring.py` | Export record counts, loading times, query times, date coverage and storage sizes for Power BI. |
| `code/watch_csv_and_trigger_airflow.py` | Optional helper: check for source CSV changes and request an Airflow run. |
| `code/restore_oversampled_data.py` | Join the submitted CSV parts and check them to prepare the local source files. |
| `config/config.example.json` | Provide example folder paths and database settings without a private password. |
| `config/reporting_table_fields.json` | List the reporting table columns and their data types. |
| `requirements.txt` | List the Python packages needed to run the code. |
| `airflow_dags/sdi_query_layer_dag.py` | Define the `pharma_phase1` Airflow workflow with three tasks: ingestion, transformation and loading, and SQL queries. |
| `sql/01_sales_by_medicine_month_channel_city.sql` | Summarize medicine sales by month, channel and city. |
| `sql/02_hospital_forecast_consumption.sql` | Compare hospital forecasts with actual consumption and show unmet demand. |
| `sql/03_sales_and_demand_side_by_side.sql` | Compare hospital pharmacy sales and hospital demand for the same medicine and month. |