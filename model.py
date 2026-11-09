"""Step 2: validate, transform and load the two facts and seven dimensions.

The field list comes from Hiba and Bilqees' final workbook.
The source files remain unchanged. Facts accumulate between successful runs.
"""
import json
from contextlib import contextmanager
from datetime import date
from pathlib import Path
import duckdb
from ingest import FILES

SPEC = json.loads((Path(__file__).parent / "table_fields.json").read_text(encoding="utf-8"))


def ident(value):
    return '"' + value.replace('"', '""') + '"'


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def columns(table):
    return list(SPEC[table])


def typed(field, expr=None):
    typ = next((fields[field] for fields in SPEC.values() if field in fields), "VARCHAR")
    expr = expr or ident(field)
    return f"CAST({expr} AS {typ}) AS {ident(field)}"


@contextmanager
def lock(cfg):
    path = cfg["work_folder"] / "pipeline.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = path.open("x")
    except FileExistsError:
        raise RuntimeError("Another load is running. If it crashed, check no load is active before removing data/pipeline.lock.")
    try:
        handle.write("One writer at a time\n"); handle.close()
        yield
    finally:
        path.unlink(missing_ok=True)


def initialize(con):
    for table, fields in SPEC.items():
        declarations = []
        for i, (field, typ) in enumerate(fields.items()):
            declarations.append(ident(field) + " " + typ + (" PRIMARY KEY" if i == 0 else ""))
        con.execute(f"CREATE TABLE IF NOT EXISTS {ident(table)} ({', '.join(declarations)})")
    con.execute("CREATE TABLE IF NOT EXISTS LoadLog (Batch VARCHAR PRIMARY KEY, LoadedAt TIMESTAMP DEFAULT current_timestamp)")
    con.execute("CREATE TABLE IF NOT EXISTS SourceHashes (Source VARCHAR, ID VARCHAR, Fingerprint VARCHAR, PRIMARY KEY(Source, ID))")
    # Key 0 has a real parent row, including the Unknown date row.
    for table, fields in SPEC.items():
        if not table.startswith("Dim"):
            continue
        row = []
        for field, typ in fields.items():
            row.append(0 if typ in ("BIGINT", "INTEGER") or typ.startswith("DECIMAL") else
                       date(1900, 1, 1) if typ == "DATE" else "Unknown")
        key = columns(table)[0]
        con.execute(f"INSERT INTO {ident(table)} VALUES ({','.join('?' for _ in row)}) ON CONFLICT ({ident(key)}) DO NOTHING", row)
    con.execute("""INSERT INTO DimDate
       SELECT CAST(strftime(d, '%Y%m%d') AS BIGINT), CAST(d AS DATE), year(d), quarter(d),
              month(d), strftime(d, '%B'), day(d), strftime(d, '%A'), strftime(d, '%Y-%m')
       FROM generate_series(DATE '2023-01-01', DATE '2028-12-31', INTERVAL 1 DAY) t(d)
       ON CONFLICT (DateKey) DO NOTHING""")


def raw_tables(con, folder):
    for name, filename in FILES.items():
        con.execute(f"CREATE OR REPLACE TEMP TABLE raw_{name} AS SELECT * FROM read_csv(?, header=true, all_varchar=true)", [str(folder / filename)])
        desc = con.execute(f"DESCRIBE raw_{name}").fetchall()
        # Trim all text while preserving leading zeros. Empty source cells become NULL.
        exprs = [f"NULLIF(trim({ident(r[0])}), '') AS {ident(r[0])}" for r in desc]
        con.execute(f"CREATE OR REPLACE TEMP TABLE raw_{name} AS SELECT {','.join(exprs)} FROM raw_{name}")
        for field in ["MedicineID", "PharmacyID", "HospitalID", "HospitalPharmacyID", "PharmacyState", "State", "CountryCode"]:
            if field in [r[0] for r in desc]:
                con.execute(f"UPDATE raw_{name} SET {ident(field)} = upper({ident(field)})")


def validate(con):
    errors = []
    def check(name, sql):
        n = con.execute(sql).fetchone()[0]
        if n:
            errors.append(f"{name}: {n} rows/groups")
    for name, key in [("master", "MedicineID"), ("sales", "SalesTransactionID"), ("demand", "HospitalDemandRecordID")]:
        check(f"Missing {key}", f"SELECT count(*) FROM raw_{name} WHERE {ident(key)} IS NULL")
        check(f"Duplicate {key}", f"SELECT count(*) FROM (SELECT {ident(key)} FROM raw_{name} GROUP BY 1 HAVING count(*)>1)")
    check("Repeated hospital medicine month", "SELECT count(*) FROM (SELECT HospitalID, MedicineID, DemandMonth FROM raw_demand GROUP BY ALL HAVING count(*)>1)")
    for src in ["sales", "demand"]:
        check(f"Missing or unknown medicine in {src}", f"SELECT count(*) FROM raw_{src} s LEFT JOIN raw_master m USING(MedicineID) WHERE m.MedicineID IS NULL")
    for src, fields in [("sales", ["SalesDate", "BatchExpiryDate"]), ("demand", ["DemandMonth"])]:
        for field in fields:
            check(f"Invalid {field}", f"SELECT count(*) FROM raw_{src} WHERE try_cast({ident(field)} AS DATE) IS NULL OR try_cast({ident(field)} AS DATE) NOT BETWEEN DATE '2023-01-01' AND DATE '2028-12-31'")
    check("DemandMonth must be month start", "SELECT count(*) FROM raw_demand WHERE day(try_cast(DemandMonth AS DATE)) <> 1")
    check("Missing PharmacyID", "SELECT count(*) FROM raw_sales WHERE PharmacyID IS NULL")
    check("Missing HospitalID", "SELECT count(*) FROM raw_demand WHERE HospitalID IS NULL")
    for src, fields in [("sales", ["PharmacyCity", "PharmacyState", "CountryCode"]), ("demand", ["City", "State", "CountryCode"])]:
        check(f"Missing location in {src}", f"SELECT count(*) FROM raw_{src} WHERE " + ' OR '.join(ident(k)+' IS NULL' for k in fields))
    check("Invalid GTIN", "SELECT count(*) FROM raw_master WHERE GTIN14 IS NULL OR NOT regexp_full_match(GTIN14, '[0-9]{14}')")
    check("Invalid cold chain flag", "SELECT count(*) FROM raw_master WHERE ColdChainFlag IS NULL OR ColdChainFlag NOT IN ('Y','N')")
    # Every selected numeric source value must parse. Facts need non-null measures.
    for src, table in [("master", "DimMedicine"), ("sales", "FactPharmacySales"), ("demand", "FactHospitalDemand")]:
        available = {r[0] for r in con.execute(f"DESCRIBE raw_{src}").fetchall()}
        for field, typ in SPEC[table].items():
            if field in available and (typ in ("BIGINT", "INTEGER") or typ.startswith("DECIMAL")):
                check(f"Invalid number {src}.{field}", f"SELECT count(*) FROM raw_{src} WHERE try_cast({ident(field)} AS {typ}) IS NULL")
    check("Invalid sold/returned packs or price", """SELECT count(*) FROM raw_sales WHERE
         try_cast(QuantitySoldPacks AS BIGINT)<=0 OR try_cast(ReturnedQuantityPacks AS BIGINT)<0
         OR try_cast(ReturnedQuantityPacks AS BIGINT)>try_cast(QuantitySoldPacks AS BIGINT)
         OR try_cast(UnitRetailPriceUSD AS DOUBLE)<=0""")
    for label, expr in [
        ("Gross sales", "QuantitySoldPacks::DOUBLE * UnitRetailPriceUSD::DOUBLE - GrossSalesAmountUSD::DOUBLE"),
        ("Net sales", "GrossSalesAmountUSD::DOUBLE - DiscountAmountUSD::DOUBLE - NetSalesAmountUSD::DOUBLE"),
        ("Gross profit", "NetSalesAmountUSD::DOUBLE - CostOfGoodsSoldUSD::DOUBLE - GrossMarginUSD::DOUBLE")]:
        # Run arithmetic only after parsing checks have passed.
        if not errors:
            check(label + " does not reconcile", f"SELECT count(*) FROM raw_sales WHERE abs({expr})>0.011")
    if not errors:
        quantities=[k for k,t in SPEC['FactHospitalDemand'].items() if t=='BIGINT' and k not in ['DemandKey','DemandDateKey','MedicineKey','HospitalKey','DemandStatusKey']]
        check("Negative hospital quantity", "SELECT count(*) FROM raw_demand WHERE " + ' OR '.join(ident(k)+'::BIGINT<0' for k in quantities))
        check("Expiry days mismatch", "SELECT count(*) FROM raw_sales WHERE BatchExpiryDate::DATE - SalesDate::DATE <> DaysToExpiryAtSale::INTEGER OR BatchExpiryDate::DATE < SalesDate::DATE")
        check("Hospital balance mismatch", "SELECT count(*) FROM raw_demand WHERE OpeningStockPacks::BIGINT + ReceivedQuantityPacks::BIGINT - DispensedQuantityPacks::BIGINT - WastageQuantityPacks::BIGINT <> ClosingStockPacks::BIGINT")
        check("Approval above request", "SELECT count(*) FROM raw_demand WHERE ApprovedQuantityPacks::BIGINT>RequestedQuantityPacks::BIGINT")
        check("Invalid stockout days", "SELECT count(*) FROM raw_demand WHERE StockoutDays::BIGINT<0 OR StockoutDays::BIGINT>day(last_day(DemandMonth::DATE))")
    if errors:
        raise ValueError("Data checks failed. No mart changes saved.\n" + "\n".join(errors))


def entity_view(con, table, src, mapping, derived):
    fields = [x for x in columns(table)[1:] if x not in ["ValidFrom", "ValidTo", "IsCurrent"]]
    exprs = []
    for field in fields:
        expr = derived.get(field, ident(mapping.get(field, field)))
        exprs.append(typed(field, expr))
    con.execute(f"CREATE OR REPLACE TEMP VIEW incoming_{table} AS SELECT DISTINCT {','.join(exprs)} FROM raw_{src}")
    natural = fields[0]
    if con.execute(f"SELECT count(*) FROM (SELECT {ident(natural)} FROM incoming_{table} GROUP BY 1 HAVING count(*)>1)").fetchone()[0]:
        raise ValueError(f"Conflicting details within source for {table}. Review before loading.")


def load_entity(con, table, type2, cfg):
    """Type 1 corrects in place. Type 2 adds an effective dated version."""
    names = columns(table); key, natural = names[:2]
    items = con.execute(f"SELECT * FROM incoming_{table}").fetchall()
    in_fields = [r[0] for r in con.description]
    for values in items:
        incoming = dict(zip(in_fields, values))
        old = con.execute(f"SELECT * FROM {table} WHERE {natural}=? AND IsCurrent=1", [incoming[natural]]).fetchone()
        existing = dict(zip(names, old)) if old else None
        changed = existing and any(existing[k] != incoming[k] for k in type2)
        if changed:
            effective = cfg.get("change_effective_date")
            if not effective:
                raise ValueError(f"Real change detected in {table} {incoming[natural]}. Set change_effective_date before creating its dated version.")
            effective = date.fromisoformat(effective)
            if effective <= existing["ValidFrom"]:
                raise ValueError("Change date must be after the current version start date.")
            con.execute(f"UPDATE {table} SET ValidTo=?, IsCurrent=0 WHERE {key}=?", [effective, existing[key]])
        if not existing or changed:
            number = con.execute(f"SELECT coalesce(max({key}),0)+1 FROM {table}").fetchone()[0]
            start = effective if changed else date.fromisoformat(cfg["baseline_date"])
            values = [number] + [incoming.get(k) for k in names[1:-3]] + [start, date(9999,12,31), 1]
            con.execute(f"INSERT INTO {table} VALUES ({','.join('?' for _ in values)})", values)
        else:
            attrs = [k for k in in_fields if k != natural and k not in type2]
            con.execute(f"UPDATE {table} SET {','.join(ident(k)+'=?' for k in attrs)} WHERE {key}=?", [incoming[k] for k in attrs]+[existing[key]])


def load_categories(con, table, view):
    fields = columns(table); key = fields[0]; attrs = fields[1:]
    same = " AND ".join(f"d.{ident(k)} IS NOT DISTINCT FROM s.{ident(k)}" for k in attrs)
    projection = ','.join('s.'+ident(k) for k in attrs)
    con.execute(f"""INSERT INTO {table} SELECT (SELECT coalesce(max({key}),0) FROM {table}) + row_number() OVER (ORDER BY {projection}), {projection}
       FROM {view} s WHERE NOT EXISTS (SELECT 1 FROM {table} d WHERE {same})""")


def build_dimensions(con, cfg):
    con.execute("""CREATE OR REPLACE TEMP VIEW locations AS
      SELECT DISTINCT PharmacyCity City, PharmacyState State, CountryCode FROM raw_sales
      UNION SELECT DISTINCT City, State, CountryCode FROM raw_demand""")
    load_categories(con, "DimLocation", "locations")
    # Resolve place keys separately for each source. Do not replace hospital places with pharmacy places.
    con.execute("""CREATE OR REPLACE TEMP TABLE raw_sales AS SELECT s.*, l.LocationKey
      FROM raw_sales s JOIN DimLocation l ON s.PharmacyCity=l.City AND s.PharmacyState=l.State AND s.CountryCode=l.CountryCode""")
    con.execute("""CREATE OR REPLACE TEMP TABLE raw_demand AS SELECT s.*, l.LocationKey
      FROM raw_demand s JOIN DimLocation l ON s.City=l.City AND s.State=l.State AND s.CountryCode=l.CountryCode""")
    entity_view(con, "DimMedicine", "master", {}, {
        "DosageFormStrengthLabel": "DosageForm || ' ' || Strength",
        "PackSizeBand": "CASE WHEN PackSize::INTEGER<=15 THEN 'Small' ELSE 'Large' END",
        "ShelfLifeBand": "CASE ShelfLifeMonths::INTEGER WHEN 24 THEN 'Shorter' WHEN 36 THEN 'Longer' ELSE 'Other' END"})
    entity_view(con, "DimPharmacy", "sales", {}, {"HospitalID": "coalesce(HospitalID, '')"})
    entity_view(con, "DimHospital", "demand", {}, {
        "TraumaLevel": "coalesce(TraumaLevel, 'Not designated')",
        "BedSizeBand": "CASE WHEN LicensedBeds::INTEGER<300 THEN 'Small' WHEN LicensedBeds::INTEGER<600 THEN 'Medium' ELSE 'Large' END"})
    load_entity(con, "DimMedicine", ["DiseaseCategory", "TherapeuticClass", "ColdChainFlag", "UnitManufacturingCostUSD", "WholesalePriceUSD", "RecommendedRetailPriceUSD"], cfg)
    load_entity(con, "DimPharmacy", ["PharmacyType", "LocationKey"], cfg)
    load_entity(con, "DimHospital", ["HospitalType", "LicensedBeds", "ICUBeds", "CatchmentPopulation", "LocationKey", "AverageOccupancyRatePct"], cfg)
    con.execute("UPDATE raw_sales SET PromotionCode='No promotion' WHERE PromotionCode IS NULL OR lower(PromotionCode) IN ('none','no promotion','no promo','not applicable')")
    for table, src in [("DimSalesProfile", "sales"), ("DimDemandStatus", "demand")]:
        attrs = columns(table)[1:]
        # Unknown category text preserves the difference from a meaningful zero.
        exprs = [f"coalesce({ident(k)}, 'Unknown') AS {ident(k)}" for k in attrs]
        con.execute(f"CREATE OR REPLACE TEMP VIEW categories_{table} AS SELECT DISTINCT {','.join(exprs)} FROM raw_{src}")
        load_categories(con, table, "categories_"+table)


def build_facts(con):
    for source, table, source_id, eventdate, place, place_natural, profile in [
        ("sales", "FactPharmacySales", "SalesTransactionID", "SalesDate", "Pharmacy", "PharmacyID", "SalesProfile"),
        ("demand", "FactHospitalDemand", "HospitalDemandRecordID", "DemandMonth", "Hospital", "HospitalID", "DemandStatus")]:
        # Detect source corrections instead of silently changing historical events.
        # Event values are immutable. Descriptive corrections may still use Type 1.
        # Do not fingerprint pharmacy names, hospital capacity or location words.
        available = {r[0] for r in con.execute(f"DESCRIBE raw_{source}").fetchall()}
        raw_cols = [k for k in columns(table)[1:] if k in available]
        raw_cols += ["MedicineID",place_natural,eventdate]
        if source=='sales': raw_cols += ['BatchExpiryDate']
        raw_cols += columns('Dim'+profile)[1:]
        raw_cols = list(dict.fromkeys(raw_cols))
        struct = ','.join(ident(k) for k in raw_cols)
        con.execute(f"CREATE OR REPLACE TEMP VIEW hashes_{source} AS SELECT {source_id} ID, sha256(to_json(row({struct}))) Fingerprint FROM raw_{source}")
        changed = con.execute(f"SELECT count(*) FROM hashes_{source} n JOIN SourceHashes h ON h.Source=? AND h.ID=n.ID WHERE h.Fingerprint<>n.Fingerprint", [source]).fetchone()[0]
        if changed:
            raise ValueError(f"{changed} existing {source} records were edited. Review source corrections before reloading.")
        category_fields = columns("Dim"+profile)[1:]
        category_match = ' AND '.join(f"c.{ident(k)}=coalesce(s.{ident(k)}, 'Unknown')" for k in category_fields)
        join = f"""FROM raw_{source} s
          LEFT JOIN DimMedicine m ON m.MedicineID=s.MedicineID AND s.{eventdate}::DATE>=m.ValidFrom AND s.{eventdate}::DATE<m.ValidTo
          LEFT JOIN Dim{place} p ON p.{place_natural}=s.{place_natural} AND s.{eventdate}::DATE>=p.ValidFrom AND s.{eventdate}::DATE<p.ValidTo
          LEFT JOIN Dim{profile} c ON {category_match}"""
        expressions = []
        overrides = {"MedicineKey": "coalesce(m.MedicineKey,0)", place+"Key": f"coalesce(p.{place}Key,0)",
            profile+"Key": f"coalesce(c.{profile}Key,0)", "SalesLineCount": "1",
            "SalesDateKey": "strftime(s.SalesDate::DATE,'%Y%m%d')", "ExpiryDateKey": "strftime(s.BatchExpiryDate::DATE,'%Y%m%d')",
            "DemandDateKey": "strftime(s.DemandMonth::DATE,'%Y%m%d')", "DaysToExpiryAtSale": "s.BatchExpiryDate::DATE-s.SalesDate::DATE"}
        for field in columns(table)[1:]:
            expressions.append(typed(field, overrides.get(field, 's.'+ident(field))))
        con.execute(f"CREATE OR REPLACE TEMP TABLE incoming_{table} AS SELECT {','.join(expressions)} {join}")
        key = columns(table)[0]
        con.execute(f"""INSERT INTO {table} SELECT (SELECT coalesce(max({key}),0) FROM {table})+row_number() OVER (ORDER BY n.{source_id}), n.*
          FROM incoming_{table} n WHERE NOT EXISTS (SELECT 1 FROM {table} f WHERE f.{source_id}=n.{source_id})""")
        con.execute(f"INSERT INTO SourceHashes SELECT ?, ID, Fingerprint FROM hashes_{source} ON CONFLICT DO NOTHING", [source])


def audit(con):
    links = [("DimPharmacy","LocationKey","DimLocation"),("DimHospital","LocationKey","DimLocation"),
             ("FactPharmacySales","MedicineKey","DimMedicine"),("FactPharmacySales","PharmacyKey","DimPharmacy"),
             ("FactPharmacySales","SalesProfileKey","DimSalesProfile"),("FactPharmacySales","SalesDateKey","DimDate"),
             ("FactPharmacySales","ExpiryDateKey","DimDate"),("FactHospitalDemand","MedicineKey","DimMedicine"),
             ("FactHospitalDemand","HospitalKey","DimHospital"),("FactHospitalDemand","DemandStatusKey","DimDemandStatus"),
             ("FactHospitalDemand","DemandDateKey","DimDate")]
    for table, field, parent in links:
        pk = columns(parent)[0]
        missing = con.execute(f"SELECT count(*) FROM {table} f LEFT JOIN {parent} d ON f.{field}=d.{pk} WHERE d.{pk} IS NULL").fetchone()[0]
        if missing:
            raise ValueError(f"Broken relationship: {table}.{field}")
    for table, source_id in [("FactPharmacySales","SalesTransactionID"),("FactHospitalDemand","HospitalDemandRecordID")]:
        total, unique = con.execute(f"SELECT count(*),count(DISTINCT {source_id}) FROM {table}").fetchone()
        if total != unique:
            raise ValueError(f"Duplicate fact rows in {table}")
    repeated_grains=con.execute("""SELECT count(*) FROM (
        SELECT h.HospitalID,m.MedicineID,f.DemandDateKey
        FROM FactHospitalDemand f JOIN DimHospital h USING(HospitalKey)
        JOIN DimMedicine m USING(MedicineKey)
        GROUP BY h.HospitalID,m.MedicineID,f.DemandDateKey HAVING count(*)>1)""").fetchone()[0]
    if repeated_grains:
        raise ValueError("Duplicate hospital medicine month across load history. No changes saved.")
    unknown = {}
    for table in ["FactPharmacySales", "FactHospitalDemand"]:
        keys = [k for k in columns(table)[1:] if k.endswith("Key")]
        unknown[table] = con.execute(f"SELECT count(*) FROM {table} WHERE " + ' OR '.join(f'{k}=0' for k in keys)).fetchone()[0]
    conflicts = con.execute("""SELECT h.HospitalID, h.City HospitalCity, h.State HospitalState,
          s.PharmacyCity, s.PharmacyState FROM
          (SELECT DISTINCT HospitalID, HospitalPharmacyID, City, State FROM raw_demand) h
          JOIN (SELECT DISTINCT PharmacyID, PharmacyCity, PharmacyState FROM raw_sales) s
          ON s.PharmacyID=h.HospitalPharmacyID WHERE h.City<>s.PharmacyCity OR h.State<>s.PharmacyState""").fetchall()
    return dict(table_counts={t:con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in SPEC},
                unknown_fact_rows=unknown, foreign_key_checks=11,
                location_conflicts=[dict(zip(["HospitalID","HospitalCity","HospitalState","PharmacyCity","PharmacyState"],r)) for r in conflicts],
                note="Dimension counts include one Unknown row. Region is omitted. Band cutoffs are project assumptions.")


def load(cfg, snapshot):
    folder = Path(snapshot); manifest=json.loads((folder/"manifest.json").read_text())
    cfg["work_folder"].mkdir(parents=True,exist_ok=True)
    with lock(cfg), duckdb.connect(str(cfg["work_folder"] / "sales_demand.duckdb")) as con:
        con.execute("BEGIN TRANSACTION")
        try:
            initialize(con); raw_tables(con,folder); validate(con)
            build_dimensions(con,cfg); build_facts(con); report=audit(con)
            con.execute("INSERT INTO LoadLog(Batch) VALUES (?) ON CONFLICT DO NOTHING", [manifest["batch"]])
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
    report["staging_mode"]=manifest["mode"]
    report["batch"]=manifest["batch"]
    cfg["results_folder"].mkdir(parents=True,exist_ok=True)
    (cfg["results_folder"] / "validation.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    return report
