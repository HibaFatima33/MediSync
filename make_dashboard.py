"""Create an offline visual dashboard from the three existing query results.

Run: python make_dashboard.py
No extra packages, internet connection or Docker are needed.
"""
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from settings import settings


def read(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing {path.name}. Run run_pipeline.py first.")
    with path.open(encoding="utf-8-sig",newline="") as handle:
        return list(csv.DictReader(handle))


def make_dashboard():
    cfg=settings();folder=cfg['results_folder']
    sales=defaultdict(lambda:[0.0,0,0.0])
    for row in read(folder/'01_sales_by_medicine_month_channel_city.csv'):
        key=tuple(row[k] for k in ['YearMonth','MedicineID','GenericName','SalesChannel'])
        values=sales[key]
        values[0]+=float(row['NetSalesUSD']);values[1]+=int(row['SoldPacks']);values[2]+=float(row['GrossProfitUSD'])
    s=[list(key)+[round(v[0],2),v[1],round(v[2],2)] for key,v in sorted(sales.items())]
    h=[]
    for row in read(folder/'02_hospital_forecast_consumption.csv'):
        h.append([row[k] for k in ['YearMonth','MedicineID','HospitalID','HospitalName']]+[
            int(row[k]) for k in ['ForecastPacks','ActualConsumedPacks','UnmetPacks']])
    comparison=[]
    for row in read(folder/'03_sales_and_demand_side_by_side.csv'):
        comparison.append([row[k] for k in ['YearMonth','MedicineID','HospitalID']]+[
            int(row[k]) if row[k] else None for k in ['PharmacySoldPacks','ConsumedPacks']])
    data=dict(sales=s,hospital=h,comparison=comparison,created=datetime.now().astimezone().isoformat(timespec='seconds'))
    # Escaping prevents a source name containing HTML from ending the script tag.
    payload=json.dumps(data,separators=(',',':')).replace('<','\\u003c')
    template=Path(__file__).with_name('dashboard_template.html').read_text(encoding='utf-8')
    target=folder/'dashboard.html';target.write_text(template.replace('__DATA__',payload),encoding='utf-8')
    print('Dashboard ready:',target.resolve())
    print('Open it in your browser. Rerun this script after each successful pipeline refresh.')
    return target


if __name__=='__main__':make_dashboard()
