"""Small regression checks for the important warehouse rules."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import duckdb
from settings import settings
from ingest import ingest,FILES
from model import load


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=str(ROOT/"tests"))
        root=Path(self.temp.name)
        self.cfg=settings().copy()
        original=self.cfg["source_folder"]
        self.cfg.update(source_folder=root/"source",work_folder=root/"data",results_folder=root/"results",postgres_dsn="",change_effective_date=None)
        self.cfg["source_folder"].mkdir()
        self.rows={}
        for name,filename in FILES.items():
            with (original/filename).open(encoding="utf-8-sig",newline="") as handle:
                reader=csv.DictReader(handle);self.headers=getattr(self,"headers",{})
                self.headers[name]=reader.fieldnames
                rows=[]
                for row in reader:
                    rows.append(row)
                    if name!="master" and len(rows)>=12:break
            self.rows[name]=rows
            self.write(name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self,name):
        with (self.cfg["source_folder"]/FILES[name]).open("w",encoding="utf-8",newline="") as handle:
            writer=csv.DictWriter(handle,fieldnames=self.headers[name]);writer.writeheader();writer.writerows(self.rows[name])

    def execute(self):
        return load(self.cfg,ingest(self.cfg))

    def test_repeat_run_does_not_duplicate_facts(self):
        first=self.execute();second=self.execute()
        self.assertEqual(first["table_counts"],second["table_counts"])
        self.assertEqual(second["table_counts"]["FactPharmacySales"],12)
        self.assertEqual(second["unknown_fact_rows"]["FactPharmacySales"],0)

    def test_invalid_amount_rolls_back(self):
        before=self.execute()
        self.rows["sales"][0]["NetSalesAmountUSD"]="999999"
        self.write("sales")
        with self.assertRaisesRegex(ValueError,"does not reconcile"):
            self.execute()
        with duckdb.connect(str(self.cfg["work_folder"]/"sales_demand.duckdb")) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM FactPharmacySales").fetchone()[0],12)
            self.assertEqual(con.execute("SELECT count(*) FROM LoadLog").fetchone()[0],1)

    def test_price_change_keeps_old_medicine_version(self):
        self.execute()
        self.rows["master"][0]["RecommendedRetailPriceUSD"]="3.50"
        self.write("master")
        with self.assertRaisesRegex(ValueError,"change_effective_date"):
            self.execute()
        self.cfg["change_effective_date"]="2026-01-01"
        self.execute()
        with duckdb.connect(str(self.cfg["work_folder"]/"sales_demand.duckdb")) as con:
            rows=con.execute("SELECT IsCurrent,ValidFrom,ValidTo FROM DimMedicine WHERE MedicineID='MED001' ORDER BY ValidFrom").fetchall()
            self.assertEqual(len(rows),2)
            self.assertEqual([r[0] for r in rows],[0,1])
            self.assertEqual(str(rows[0][2]),"2026-01-01")

    def test_new_sales_append(self):
        self.execute()
        extra=self.rows['sales'][0].copy();extra['SalesTransactionID']='SALE-TEST-NEW'
        self.rows['sales'].append(extra);self.write('sales')
        report=self.execute()
        self.assertEqual(report['table_counts']['FactPharmacySales'],13)

    def test_new_id_cannot_duplicate_an_old_demand_month(self):
        self.execute()
        self.rows['demand'][0]['HospitalDemandRecordID']='HDEM-TEST-REPLACED'
        self.write('demand')
        with self.assertRaisesRegex(ValueError,'across load history'):
            self.execute()

    def test_type1_name_correction_keeps_existing_facts(self):
        self.execute()
        target=self.rows['sales'][0]['PharmacyID']
        for row in self.rows['sales']:
            if row['PharmacyID']==target:row['PharmacyName']='Corrected Pharmacy Name'
        self.write('sales')
        report=self.execute()
        self.assertEqual(report['table_counts']['FactPharmacySales'],12)
        with duckdb.connect(str(self.cfg['work_folder']/'sales_demand.duckdb')) as con:
            self.assertEqual(con.execute('SELECT PharmacyName FROM DimPharmacy WHERE PharmacyID=? AND IsCurrent=1',[target]).fetchone()[0],'Corrected Pharmacy Name')


if __name__=="__main__":unittest.main()
