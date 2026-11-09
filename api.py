"""Small localhost ingestion API using Python's standard library.

Start: python api.py
Only local file paths from config.json are accepted. No arbitrary upload paths.
Airflow calls /ingest, /load, /queries in order. /run is for local practice.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from settings import settings
from ingest import ingest
from model import load
from run_pipeline import run,run_queries


class Handler(BaseHTTPRequestHandler):
    def respond(self,code,value):
        body=json.dumps(value,default=str).encode()
        self.send_response(code);self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)

    def do_GET(self):
        if self.path=="/health":
            self.respond(200,{"status":"ready"})
        else:
            self.respond(404,{"error":"Use GET /health or POST /ingest, /load, /queries, /run"})

    def do_POST(self):
        try:
            size=int(self.headers.get("Content-Length","0"))
            if size>8192:
                raise ValueError("Request is too large")
            body=json.loads(self.rfile.read(size) or b"{}")
            cfg=settings()
            if self.path=="/ingest":
                result={"snapshot":ingest(cfg,require_postgres=body.get("require_postgres",True))}
            elif self.path=="/load":
                folder=Path(body["snapshot"]).resolve()
                if not folder.is_relative_to((cfg["work_folder"]/"batches").resolve()):
                    raise ValueError("Snapshot must be inside the configured batches folder")
                result=load(cfg,str(folder))
            elif self.path=="/queries":
                result=run_queries(cfg)
            elif self.path=="/run":
                result=run(cfg,require_postgres=body.get("require_postgres",False))
            else:
                self.respond(404,{"error":"Unknown endpoint"});return
            self.respond(200,result)
        except Exception as exc:
            # Includes real validation failures; no fake successful response.
            self.respond(400,{"error":str(exc)})


if __name__=="__main__":
    print("Local API at http://127.0.0.1:8000. Press Ctrl+C to stop.")
    HTTPServer(("127.0.0.1",8000),Handler).serve_forever()
