"""Step 1: snapshot the three files and optionally stage them in PostgreSQL."""
import csv
import hashlib
import json
import shutil
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone

FILES = {
    "master": "01_master_data.csv",
    "sales": "05_pharmacy_sales_data.csv",
    "demand": "06_hospital_demand_data.csv",
}


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def ingest(cfg, require_postgres=False):
    if require_postgres and not cfg["postgres_dsn"]:
        raise ValueError("PostgreSQL is required for this mode. Set postgres_dsn in config.json.")
    batch = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex[:8]
    folder = cfg["work_folder"] / "batches" / batch
    folder.mkdir(parents=True)
    metrics = []
    for name, filename in FILES.items():
        start = time.perf_counter()
        source = cfg["source_folder"] / filename
        target = folder / filename
        before = digest(source)
        shutil.copyfile(source, target)
        if digest(source) != before or digest(target) != before:
            raise ValueError(f"{filename} changed while being read. Try again after copying finishes.")
        with target.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            headers = next(reader)
            if len(headers) != len(set(headers)):
                raise ValueError(f"Repeated column names in {filename}")
            count = sum(1 for _ in reader)
        metrics.append(dict(source=name, rows=count, sha256=before,
                            seconds=round(time.perf_counter() - start, 3)))
    # In assignment mode, the mart reads an export FROM PostgreSQL staging.
    # In local practice mode, it reads the immutable copies above.
    if cfg["postgres_dsn"]:
        stage_metrics=stage_postgres(folder, batch, cfg["postgres_dsn"])
        for item in metrics:
            item['snapshot_seconds']=item.pop('seconds')
            item.update(stage_metrics[item['source']])
            if item['rows']!=item['postgres_rows']:
                raise ValueError('PostgreSQL count differs from the source snapshot')
    manifest = dict(batch=batch, mode="postgres" if cfg["postgres_dsn"] else "local_practice",
                    metrics=metrics, snapshot=str(folder.resolve()))
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return str(folder.resolve())


def stage_postgres(folder, batch, dsn):
    import psycopg
    from psycopg import sql
    # This transaction replaces only raw staging snapshots. It never empties facts.
    metrics={}
    with psycopg.connect(dsn, connect_timeout=10) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(7142026)")
        conn.execute("CREATE SCHEMA IF NOT EXISTS pharma_staging")
        for name, filename in FILES.items():
            start=time.perf_counter()
            path = folder / filename
            with path.open(encoding="utf-8-sig", newline="") as handle:
                headers = next(csv.reader(handle))
            table = sql.Identifier("pharma_staging", "raw_" + name)
            columns = sql.SQL(", ").join(sql.SQL("{} TEXT").format(sql.Identifier(h)) for h in headers)
            conn.execute(sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(table, columns))
            conn.execute(sql.SQL("TRUNCATE TABLE {}").format(table))
            with conn.cursor() as cur:
                with cur.copy(sql.SQL("COPY {} FROM STDIN WITH (FORMAT CSV, HEADER TRUE)").format(table)) as copy:
                    with path.open("rb") as handle:
                        # Strip UTF-8 BOM if present. PostgreSQL column names remain unchanged.
                        prefix = handle.read(3)
                        if prefix != b"\xef\xbb\xbf":
                            handle.seek(0)
                        while block := handle.read(1024 * 1024):
                            copy.write(block)
                export = path.with_suffix(".staged.csv")
                with cur.copy(sql.SQL("COPY {} TO STDOUT WITH (FORMAT CSV, HEADER TRUE)").format(table)) as copy:
                    with export.open("wb") as handle:
                        for block in copy:
                            handle.write(block)
                export.replace(path)
            count=conn.execute(sql.SQL('SELECT count(*) FROM {}').format(table)).fetchone()[0]
            metrics[name]=dict(postgres_rows=count,staging_seconds=round(time.perf_counter()-start,3))
        conn.execute("""CREATE TABLE IF NOT EXISTS pharma_staging.batch_log
                        (batch_id TEXT PRIMARY KEY, loaded_at TIMESTAMPTZ DEFAULT now())""")
        conn.execute("INSERT INTO pharma_staging.batch_log(batch_id) VALUES (%s)", (batch,))
    return metrics
