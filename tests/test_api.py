"""Check the real local HTTP endpoints on a small source fixture."""
import json
import sys
import threading
import unittest
import urllib.request
from pathlib import Path
from http.server import HTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import test_pipeline as fixture_module
import api


class ApiTest(unittest.TestCase):
    def test_http_ingest_load_queries(self):
        fixture=fixture_module.PipelineTests();fixture.setUp()
        previous=api.settings
        api.settings=lambda:fixture.cfg
        server=HTTPServer(('127.0.0.1',0),api.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base='http://127.0.0.1:'+str(server.server_port)
        def post(path,body):
            request=urllib.request.Request(base+path,json.dumps(body).encode(),{'Content-Type':'application/json'},method='POST')
            with urllib.request.urlopen(request,timeout=120) as response:return json.load(response)
        try:
            with urllib.request.urlopen(base+'/health') as response:self.assertEqual(json.load(response)['status'],'ready')
            snap=post('/ingest',{'require_postgres':False})['snapshot']
            report=post('/load',{'snapshot':snap})
            self.assertEqual(report['table_counts']['FactPharmacySales'],12)
            results=post('/queries',{})
            self.assertEqual(len(results['queries']),3)
        finally:
            server.shutdown();server.server_close();thread.join()
            api.settings=previous;fixture.tearDown()


if __name__=='__main__':unittest.main()
