"""Check new-month generation, retry deduplication and interrupted publication."""
import csv
import json
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

MILESTONE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(MILESTONE/'code'))
import test_pipeline
import generate_demo_records as generator


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=test_pipeline.PipelineTests()
        self.fixture.setUp()
        self.cfg=self.fixture.cfg
        for row in self.fixture.rows['sales']:
            row['BatchExpiryDate']='2028-12-31'
            row['DaysToExpiryAtSale']=str((date(2028,12,31)-date.fromisoformat(row['SalesDate'])).days)
        self.fixture.write('sales')
        (self.cfg['source_folder']/'demo_state.json').write_text(json.dumps({'completed':[1,2]}),encoding='utf-8')

    def tearDown(self):
        self.fixture.tearDown()

    def sales(self):
        return list(generator.read_rows(self.cfg['source_folder']/generator.FILES['sales']))

    def test_next_month_and_same_request_retry(self):
        original=self.sales()
        first=generator.generate_refresh(sales_count=5,cfg=self.cfg,request_id='run-march')
        self.assertEqual(first['period'],'2026-03')
        self.assertEqual(first['new_sales'],5)
        self.assertEqual(self.sales()[:len(original)],original)
        repeat=generator.generate_refresh(sales_count=5,cfg=self.cfg,request_id='run-march')
        self.assertEqual(repeat['status'],'already_completed')
        self.assertEqual(len(self.sales()),len(original)+5)
        second=generator.generate_refresh(sales_count=5,cfg=self.cfg,request_id='run-april')
        self.assertEqual(second['period'],'2026-04')
        self.assertEqual(len(self.sales()),len(original)+10)

    def test_interrupted_publication_is_completed_on_retry(self):
        original=self.sales()
        publish=generator.publish_generation
        def interrupt_after_first_file(folder):
            journal_path=folder/'generation.pending.json'
            if journal_path.exists():
                item=json.loads(journal_path.read_text())['files'][0]
                (folder/item['temporary']).replace(folder/item['target'])
                raise OSError('Simulated interruption after the sales file')
            publish(folder)
        with patch.object(generator,'publish_generation',side_effect=interrupt_after_first_file):
            with self.assertRaisesRegex(OSError,'Simulated interruption'):
                generator.generate_refresh(sales_count=5,cfg=self.cfg,request_id='interrupted-run')
        result=generator.generate_refresh(sales_count=5,cfg=self.cfg,request_id='interrupted-run')
        self.assertEqual(result['status'],'already_completed')
        self.assertEqual(len(self.sales()),len(original)+5)
        self.assertFalse((self.cfg['source_folder']/'generation.pending.json').exists())
        ids=[row['SalesTransactionID'] for row in self.sales()]
        self.assertEqual(len(ids),len(set(ids)))

    def test_invalid_count_leaves_source_unchanged(self):
        original=self.sales()
        with self.assertRaises(ValueError):
            generator.generate_refresh(sales_count=0,cfg=self.cfg,request_id='invalid-run')
        self.assertEqual(self.sales(),original)


if __name__=='__main__':unittest.main()
