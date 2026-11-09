"""Run this file from the VS Code terminal. No Docker is used."""
import argparse
import csv
import json
import time
from pathlib import Path
from datetime import datetime,timezone
import duckdb
from settings import ROOT, settings
from ingest import ingest
from model import load, lock


def run_queries(cfg):
    cfg["results_folder"].mkdir(parents=True, exist_ok=True)
    metrics=[]
    with lock(cfg), duckdb.connect(str(cfg["work_folder"] / "sales_demand.duckdb"),read_only=True) as con:
        for path in sorted((ROOT/"sql").glob("*.sql")):
            start=time.perf_counter()
            result=con.execute(path.read_text(encoding="utf-8"))
            headers=[r[0] for r in result.description]
            out=cfg["results_folder"]/(path.stem+".csv")
            rows=0
            with out.open("w",encoding="utf-8-sig",newline="") as handle:
                writer=csv.writer(handle);writer.writerow(headers)
                while chunk:=result.fetchmany(10000):
                    writer.writerows(chunk);rows+=len(chunk)
            metrics.append(dict(query=path.name,rows=rows,seconds=round(time.perf_counter()-start,4),success=True))
        counts=con.execute("SELECT count(*) FROM LoadLog").fetchone()[0]
    (cfg["results_folder"]/"query_metrics.json").write_text(json.dumps(metrics,indent=2),encoding="utf-8")
    return dict(queries=metrics,successful_loads=counts)


def run(cfg=None, require_postgres=False):
    cfg=cfg or settings()
    start=time.perf_counter()
    try:
        snapshot=ingest(cfg,require_postgres=require_postgres)
        report=load(cfg,snapshot)
        report.update(run_queries(cfg))
    except Exception as exc:
        cfg['results_folder'].mkdir(parents=True,exist_ok=True)
        with (cfg['results_folder']/'attempts.jsonl').open('a',encoding='utf-8') as handle:
            handle.write(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(),success=False,error=str(exc),seconds=round(time.perf_counter()-start,3)))+'\n')
        raise
    report["total_seconds"]=round(time.perf_counter()-start,3)
    (cfg["results_folder"]/"run_summary.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    with (cfg['results_folder']/'attempts.jsonl').open('a',encoding='utf-8') as handle:
        handle.write(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(),success=True,seconds=report['total_seconds']))+'\n')
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Hiba and Bilqees Phase 1 pipeline without Docker")
    parser.add_argument("--require-postgres",action="store_true",help="Fail instead of using local practice staging")
    parser.add_argument("--queries-only",action="store_true",help="Run SQL against the existing mart")
    args=parser.parse_args()
    print(json.dumps(run_queries(settings()) if args.queries_only else run(require_postgres=args.require_postgres),indent=2))
