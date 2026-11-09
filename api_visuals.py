"""
New API version with dashboard generation.
The original api.py stays unchanged.
"""

import argparse
from http.server import HTTPServer

from api import Handler as OriginalHandler
from make_dashboard import make_dashboard


class RefreshHandler(OriginalHandler):

    def do_POST(self):
        if self.path == "/dashboard":
            try:
                dashboard = make_dashboard()

                self.respond(
                    200,
                    {
                        "status": "success",
                        "dashboard": str(dashboard)
                    }
                )

            except Exception as error:
                self.respond(
                    400,
                    {"error": str(error)}
                )

        else:
            # Reuse the existing ingestion, loading and SQL endpoints.
            super().do_POST()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--host",
        default="127.0.0.1"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8765
    )

    arguments = parser.parse_args()

    server = HTTPServer(
        (arguments.host, arguments.port),
        RefreshHandler
    )

    print(
        f"API ready at "
        f"http://{arguments.host}:{arguments.port}",
        flush=True
    )

    server.serve_forever()