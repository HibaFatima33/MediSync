"""
Export pipeline monitoring data for Power BI.

Run after Airflow finishes.
This script reads the databases without changing records.
"""

import csv
import json
import time

from datetime import datetime

import duckdb

from settings import ROOT, settings


def save_csv(folder, filename, headers, rows):
    path = folder / filename

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def export_monitoring():
    cfg = settings()

    output = cfg["results_folder"] / "monitoring"

    output.mkdir(
        parents=True,
        exist_ok=True
    )

    validation_path = (
        cfg["results_folder"] / "validation.json"
    )

    validation = json.loads(
        validation_path.read_text(
            encoding="utf-8"
        )
    )

    batch = validation["batch"]

    manifest_path = (
        cfg["work_folder"]
        / "batches"
        / batch
        / "manifest.json"
    )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    measured_at = (
        datetime.now()
        .astimezone()
        .isoformat(timespec="seconds")
    )

    # 1. Source ingestion measurements
    ingestion_rows = []

    for item in manifest["metrics"]:
        snapshot_seconds = item.get(
            "snapshot_seconds",
            item.get("seconds")
        )

        staging_seconds = item.get(
            "staging_seconds"
        )

        ingestion_rows.append([
            batch,
            item["source"],
            item["rows"],
            snapshot_seconds,
            staging_seconds,
            manifest["mode"],
            measured_at
        ])

    save_csv(
        output,
        "ingestion.csv",
        [
            "Batch",
            "Source",
            "RowsProcessed",
            "SnapshotSeconds",
            "StagingSeconds",
            "Mode",
            "MeasuredAt"
        ],
        ingestion_rows
    )

    database = (
        cfg["work_folder"]
        / "sales_demand.duckdb"
    )

    table_rows = []
    query_rows = []
    coverage_rows = []

    with duckdb.connect(
        str(database),
        read_only=True
    ) as connection:

        # 2. Dimension and fact row counts
        tables = connection.execute(
            "SHOW TABLES"
        ).fetchall()

        for (table_name,) in tables:
            if not table_name.startswith(
                ("Dim", "Fact")
            ):
                continue

            safe_name = table_name.replace(
                '"',
                '""'
            )

            row_count = connection.execute(
                f'SELECT COUNT(*) FROM "{safe_name}"'
            ).fetchone()[0]

            table_type = (
                "Dimension"
                if table_name.startswith("Dim")
                else "Fact"
            )

            table_rows.append([
                table_name,
                row_count,
                table_type,
                measured_at
            ])

        # 3. Measure the three SQL queries
        for sql_file in sorted(
            (ROOT / "sql").glob("*.sql")
        ):
            started = time.perf_counter()

            result = connection.execute(
                sql_file.read_text(
                    encoding="utf-8"
                )
            )

            result_count = 0

            while True:
                chunk = result.fetchmany(10000)

                if not chunk:
                    break

                result_count += len(chunk)

            milliseconds = round(
                (
                    time.perf_counter()
                    - started
                ) * 1000,
                3
            )

            query_rows.append([
                sql_file.stem,
                milliseconds,
                result_count,
                "Success",
                measured_at
            ])

        # 4. Actual date coverage in each fact
        fact_dates = [
            (
                "FactPharmacySales",
                "SalesDateKey"
            ),
            (
                "FactHospitalDemand",
                "DemandDateKey"
            )
        ]

        for table_name, date_key in fact_dates:
            first_date, last_date, months = (
                connection.execute(
                    f"""
                    SELECT
                        MIN(d.FullDate),
                        MAX(d.FullDate),
                        COUNT(DISTINCT d.YearMonth)
                    FROM {table_name} f
                    JOIN DimDate d
                      ON d.DateKey = f.{date_key}
                    WHERE d.DateKey <> 0
                    """
                ).fetchone()
            )

            coverage_rows.append([
                table_name,
                first_date,
                last_date,
                months,
                measured_at
            ])

    save_csv(
        output,
        "tables.csv",
        [
            "TableName",
            "RowCount",
            "TableType",
            "MeasuredAt"
        ],
        table_rows
    )

    save_csv(
        output,
        "queries.csv",
        [
            "Query",
            "Milliseconds",
            "ResultRows",
            "Status",
            "MeasuredAt"
        ],
        query_rows
    )

    save_csv(
        output,
        "coverage.csv",
        [
            "TableName",
            "FirstDate",
            "LastDate",
            "MonthsPresent",
            "MeasuredAt"
        ],
        coverage_rows
    )

    # 5. Database storage sizes
    storage_rows = [
        [
            "DuckDB mart",
            round(
                database.stat().st_size
                / (1024 * 1024),
                3
            ),
            measured_at
        ]
    ]

    if cfg["postgres_dsn"]:
        import psycopg

        with psycopg.connect(
            cfg["postgres_dsn"],
            connect_timeout=10
        ) as connection:

            staging_bytes = connection.execute(
                """
                SELECT COALESCE(
                    SUM(pg_total_relation_size(c.oid)),
                    0
                )
                FROM pg_class c
                JOIN pg_namespace n
                  ON n.oid = c.relnamespace
                WHERE n.nspname = 'pharma_staging'
                  AND c.relkind = 'r'
                """
            ).fetchone()[0]

            storage_rows.append([
                "PostgreSQL staging tables",
                round(
                    float(staging_bytes)
                    / (1024 * 1024),
                    3
                ),
                measured_at
            ])

    save_csv(
        output,
        "database_sizes.csv",
        [
            "Store",
            "SizeMB",
            "MeasuredAt"
        ],
        storage_rows
    )

    print("Monitoring files created:")
    print(output.resolve())
    print()
    print("1. ingestion.csv")
    print("2. tables.csv")
    print("3. queries.csv")
    print("4. coverage.csv")
    print("5. database_sizes.csv")
    print()
    print("Import these files into Power BI.")
    print(
        "Query time includes execution "
        "and fetching the result rows."
    )
    print(
        "Ingestion measurements describe "
        "the last validated batch."
    )
    print(
        "A blank staging duration means "
        "the measurement is unavailable."
    )
    print(
        "Rerun this script after another "
        "completed pipeline run."
    )


if __name__ == "__main__":
    export_monitoring()