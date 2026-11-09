"""Wait for stable file changes. Trigger Airflow, or use --practice locally.

This uses polling rather than another installed package. It does not edit files.
"""
import argparse
import json
import os
import time
import urllib.request
from settings import settings
from ingest import FILES,digest


def signatures(folder):
    return tuple((folder/n).stat().st_size for n in FILES.values()), tuple((folder/n).stat().st_mtime_ns for n in FILES.values())


def post(url,data,token=None):
    headers={"Content-Type":"application/json"}
    if token:headers["Authorization"]="Bearer "+token
    req=urllib.request.Request(url,data=json.dumps(data).encode(),headers=headers,method="POST")
    with urllib.request.urlopen(req,timeout=1800) as response:
        return json.load(response)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--practice",action="store_true")
    args=parser.parse_args();cfg=settings();folder=cfg["source_folder"]
    # None causes one initial load. Later loads require changed contents.
    last=None
    print("Watching the three selected files. Press Ctrl+C to stop.")
    while True:
        try:
            a=signatures(folder);time.sleep(5)
            if a!=signatures(folder):continue
            hashes=tuple(digest(folder/n) for n in FILES.values())
            if hashes!=last:
                if args.practice:
                    result=post("http://127.0.0.1:8000/run",{"require_postgres":False})
                else:
                    url=os.environ.get("AIRFLOW_API_URL","http://localhost:8080")
                    token=os.environ.get("AIRFLOW_API_TOKEN")
                    if not token:raise ValueError("Set AIRFLOW_API_TOKEN from your Airflow login API. Or use --practice for local testing.")
                    from datetime import datetime,timezone
                    result=post(url+"/api/v2/dags/pharma_phase1/dagRuns",{
                        "logical_date":datetime.now(timezone.utc).isoformat(),"conf":{}},token)
                last=hashes
                print("Accepted changed files:",json.dumps(result,default=str)[:400])
        except Exception as exc:
            print("Not loaded:",str(exc))
        time.sleep(10)
