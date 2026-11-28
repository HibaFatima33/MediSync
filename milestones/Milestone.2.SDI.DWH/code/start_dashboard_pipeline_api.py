"""Windows API for DWH loading and optional SDI demo-data generation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "milestones" / "Milestone.1.SDI.DWH" / "code"))
import argparse
import json
from http.server import HTTPServer
from start_query_layer_api import Handler as OriginalHandler
from generate_demo_records import generate_refresh
from project_settings import settings


class RefreshHandler(OriginalHandler):
    def do_POST(self):
        if self.path == "/generate":
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size < 0 or size > 8192:
                    raise ValueError("Invalid request size.")
                body = json.loads(self.rfile.read(size) or b"{}")
                request_id = body.get("request_id")
                if not isinstance(request_id, str) or not request_id:
                    raise ValueError("request_id must identify this Airflow run.")
                sales_rows = body.get("sales_rows", 1000)
                if isinstance(sales_rows, bool) or not isinstance(sales_rows, int) or not 1 <= sales_rows <= 10000:
                    raise ValueError("sales_rows must be a whole number from 1 to 10000.")
                self.respond(200, generate_refresh(sales_count=sales_rows, cfg=settings(), request_id=request_id))
            except Exception as error:
                self.respond(400, {"error": str(error)})
        else:
            super().do_POST()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    arguments = parser.parse_args()
    server = HTTPServer((arguments.host, arguments.port), RefreshHandler)
    print(f"API ready at http://{arguments.host}:{arguments.port}", flush=True)
    server.serve_forever()
