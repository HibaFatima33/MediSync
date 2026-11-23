"""Checks real failure logging and watcher behaviour using temporary test data."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import duckdb
import monitoring_events as events
import run_dwh_pipeline as pipeline
import watch_csv_and_trigger_airflow as watcher
from load_csv_to_postgres import ingest

class MonitoringTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.cfg=dict(results_folder=self.root/'results',work_folder=self.root/'data',source_folder=self.root/'source',postgres_dsn='')
        for k in ['results_folder','work_folder','source_folder']:self.cfg[k].mkdir()
    def tearDown(self):self.temp.cleanup()
    def test_rates_and_empty_history(self):
        self.assertIsNone(events.summaries(self.cfg)[2][3])
        events.record_event(self.cfg,'ingestion',True,1,mode='postgres')
        events.record_event(self.cfg,'ingestion',False,1,mode='postgres')
        events.record_event(self.cfg,'query',False,1,query='example.sql')
        self.assertEqual(events.summaries(self.cfg)[2],(2,1,1,50.0,50.0))
        self.assertEqual(events.summaries(self.cfg)[3][4],100.0)
    def test_failed_ingestion_is_logged_and_raised(self):
        with self.assertRaises(FileNotFoundError):ingest(self.cfg)
        rows=[json.loads(x) for x in (self.cfg['results_folder']/'monitoring_events.jsonl').read_text().splitlines()]
        self.assertFalse(rows[-1]['success'])
    def test_failed_query_preserves_old_answer_and_is_logged(self):
        sql=self.root/'sql';sql.mkdir()
        (sql/'01_bad.sql').write_text('SELECT * FROM nonexistent_table')
        output=self.cfg['results_folder']/'01_bad.csv';output.write_text('old valid result')
        with duckdb.connect(str(self.cfg['work_folder']/'sales_demand.duckdb')) as c:c.execute('CREATE TABLE LoadLog(id INTEGER)')
        with patch.object(pipeline,'SQL_DIR',sql):
            with self.assertRaises(duckdb.Error):pipeline.run_queries(self.cfg)
        self.assertEqual(output.read_text(),'old valid result')
        self.assertEqual(events.summaries(self.cfg)[3][2],1)
    def test_hashes_ignore_touch_and_detect_changed_contents(self):
        for name in watcher.FILES:(self.cfg['source_folder']/name).write_text('a')
        first=watcher.stable_hashes(self.cfg['source_folder'],0)
        (self.cfg['source_folder']/watcher.FILES[0]).touch()
        self.assertEqual(first,watcher.stable_hashes(self.cfg['source_folder'],0))
        (self.cfg['source_folder']/watcher.FILES[0]).write_text('b')
        self.assertNotEqual(first,watcher.stable_hashes(self.cfg['source_folder'],0))

if __name__=='__main__':unittest.main()
