"""
Phase 1 synthetic data generator.

Original source files are not edited.
--prepare creates a separate demo copy.
--refresh 1 adds January 2026.
--refresh 2 adds February 2026.
"""

import argparse
import calendar
import csv
import json
import os
import random
import shutil

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from settings import ROOT, settings
from ingest import FILES


def read_rows(path):
    with path.open(
        encoding="utf-8-sig",
        newline=""
    ) as handle:
        yield from csv.DictReader(handle)


def money(number):
    return Decimal(str(number)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def prepare_demo():
    cfg = settings()

    destination = cfg["work_folder"] / "demo_source"
    state_path = destination / "demo_state.json"

    if state_path.exists():
        print("Demo copy already exists. Nothing was reset.")
        return

    destination.mkdir(
        parents=True,
        exist_ok=True
    )

    if cfg["source_folder"].resolve() == destination.resolve():
        raise ValueError(
            "Demo folder has no state file. Review it first."
        )

    # Copy all three selected source files.
    for filename in FILES.values():
        shutil.copyfile(
            cfg["source_folder"] / filename,
            destination / filename
        )

    config_path = Path(
        os.environ.get(
            "PHARMA_CONFIG",
            ROOT / "config.json"
        )
    )

    original_config = (
        config_path
        if config_path.exists()
        else ROOT / "config.example.json"
    )

    config_data = json.loads(
        original_config.read_text(
            encoding="utf-8-sig"
        )
    )

    # This backup may contain the database password.
    # It stays inside the ignored data folder.
    backup = (
        cfg["work_folder"]
        / "private_config_before_demo.json"
    )

    if not backup.exists():
        shutil.copyfile(
            original_config,
            backup
        )

    # The next pipeline run will read the demo copy.
    # Other settings, including PostgreSQL, are preserved.
    config_data["source_folder"] = str(
        destination.resolve()
    )

    config_path.write_text(
        json.dumps(config_data, indent=2),
        encoding="utf-8"
    )

    state = {
        "completed": [],
        "original_source": str(cfg["source_folder"])
    }

    state_path.write_text(
        json.dumps(state, indent=2),
        encoding="utf-8"
    )

    print("Demo copy prepared.")
    print("Original CSV files are unchanged.")
    print("New source folder:", destination.resolve())


def generate_refresh(refresh_number, sales_count=1000):
    cfg = settings()
    folder = cfg["source_folder"]
    state_path = folder / "demo_state.json"

    if not state_path.exists():
        raise ValueError(
            "Run generate_demo.py --prepare first."
        )

    state = json.loads(
        state_path.read_text(encoding="utf-8")
    )

    if refresh_number in state["completed"]:
        print("This refresh already exists.")
        print("No extra rows were added.")
        return

    if (
        refresh_number == 2
        and 1 not in state["completed"]
    ):
        raise ValueError(
            "Complete refresh 1 before refresh 2."
        )

    if sales_count < 1:
        raise ValueError(
            "Sales count must be positive."
        )

    month = date(2026, refresh_number, 1)

    days_in_month = calendar.monthrange(
        month.year,
        month.month
    )[1]

    # Fixed seed makes the generation repeatable.
    rng = random.Random(
        202600 + refresh_number
    )

    master = {
        row["MedicineID"]: row
        for row in read_rows(
            folder / FILES["master"]
        )
    }

    # Select source templates whose batches will
    # still be unexpired during the new month.
    sales_templates = []

    for row in read_rows(folder / FILES["sales"]):
        expiry = date.fromisoformat(
            row["BatchExpiryDate"]
        )

        minimum_expiry = (
            month
            + timedelta(days=days_in_month + 30)
        )

        if expiry >= minimum_expiry:
            sales_templates.append(row)

        if len(sales_templates) >= 5000:
            break

    if not sales_templates:
        raise ValueError(
            "No suitable unexpired sales templates found."
        )

    # Find the latest demand record for every
    # hospital and medicine pair.
    latest_demand = {}

    for row in read_rows(folder / FILES["demand"]):
        key = (
            row["HospitalID"],
            row["MedicineID"]
        )

        if (
            key not in latest_demand
            or row["DemandMonth"]
            > latest_demand[key]["DemandMonth"]
        ):
            latest_demand[key] = row

    if any(
        date.fromisoformat(row["DemandMonth"]) >= month
        for row in latest_demand.values()
    ):
        raise ValueError(
            "The target demand month already exists. "
            "Review the demo state before continuing."
        )

    new_sales = []

    for number in range(1, sales_count + 1):
        row = rng.choice(sales_templates).copy()

        quantity = rng.randint(1, 8)

        sale_date = month + timedelta(
            days=rng.randrange(days_in_month)
        )

        transaction_id = (
            f"SYN-SDI-{month:%Y%m}-{number:06d}"
        )

        row.update({
            "SalesTransactionID": transaction_id,
            "SalesDate": sale_date.isoformat(),
            "SalesTimestampUTC": (
                sale_date.isoformat()
                + "T12:00:00Z"
            ),
            "QuantitySoldPacks": str(quantity),
            "ReturnedQuantityPacks": "0",
            "ReturnFlag": "N",
            "SaleStatus": "Completed",
            "SourceSystem": "SYNTHETIC_PHASE1_DEMO"
        })

        unit_price = Decimal(
            row["UnitRetailPriceUSD"]
        )

        gross = money(
            unit_price * quantity
        )

        # Simulation assumptions:
        # discount = 5 percent
        # tax = 6 percent of net sales
        discount = money(
            gross * Decimal("0.05")
        )

        net = gross - discount

        wholesale_price = Decimal(
            master[row["MedicineID"]]["WholesalePriceUSD"]
        )

        cost = money(
            wholesale_price * quantity
        )

        expiry = date.fromisoformat(
            row["BatchExpiryDate"]
        )

        row.update({
            "GrossSalesAmountUSD": str(gross),
            "DiscountAmountUSD": str(discount),
            "NetSalesAmountUSD": str(net),
            "CostOfGoodsSoldUSD": str(cost),
            "GrossMarginUSD": str(net - cost),
            "SalesTaxUSD": str(
                money(net * Decimal("0.06"))
            ),
            "DaysToExpiryAtSale": str(
                (expiry - sale_date).days
            ),
            "PromotionCode": "SYNTHETIC5"
        })

        if row["PrescriptionRequiredFlag"] == "Y":
            row["PrescriptionID"] = (
                f"SYN-RX-{month:%Y%m}-{number:06d}"
            )
        else:
            row["PrescriptionID"] = ""

        if row["SalesChannel"] == "Ecommerce":
            row["EcommerceDeliveryStatus"] = "Delivered"

        new_sales.append(row)

    new_demand = []

    for number, (key, previous) in enumerate(
        sorted(latest_demand.items()),
        start=1
    ):
        row = previous.copy()

        # Keep stock history connected.
        opening = int(
            previous["ClosingStockPacks"]
        )

        forecast = max(
            1,
            round(
                int(previous["ForecastDemandPacks"])
                * rng.uniform(0.90, 1.10)
            )
        )

        requested = max(
            1,
            round(
                forecast * rng.uniform(0.95, 1.12)
            )
        )

        approved = round(
            requested * rng.uniform(0.90, 1.00)
        )

        received = round(
            approved * rng.uniform(0.85, 1.00)
        )

        desired_use = max(
            1,
            round(
                forecast * rng.uniform(0.90, 1.15)
            )
        )

        available = opening + received

        dispensed = min(
            available,
            desired_use
        )

        wastage = min(
            max(0, available - dispensed),
            rng.randint(0, 2)
        )

        consumed = max(
            0,
            dispensed - rng.randint(0, 3)
        )

        unmet = max(
            0,
            desired_use - dispensed
        )

        closing = (
            opening
            + received
            - dispensed
            - wastage
        )

        # These are synthetic demonstration rules,
        # not claimed formulas from the original source.
        stockout_days = min(
            days_in_month,
            round(
                days_in_month * unmet / desired_use
            )
        )

        service_level = money(
            Decimal(dispensed) * 100 / desired_use
        )

        values = {
            "ForecastDemandPacks": forecast,
            "RequestedQuantityPacks": requested,
            "ApprovedQuantityPacks": approved,
            "ReceivedQuantityPacks": received,
            "OpeningStockPacks": opening,
            "DispensedQuantityPacks": dispensed,
            "ConsumedQuantityPacks": consumed,
            "WastageQuantityPacks": wastage,
            "ClosingStockPacks": closing,
            "UnfulfilledDemandPacks": unmet,
            "EmergencyRequestQuantityPacks": max(
                0,
                desired_use - opening - approved
            ),
            "StockoutDays": stockout_days
        }

        row.update({
            field: str(value)
            for field, value in values.items()
        })

        row.update({
            "HospitalDemandRecordID": (
                f"SYN-HDEM-{month:%Y%m}-{number:05d}"
            ),
            "DemandMonth": month.isoformat(),
            "ServiceLevelPct": str(service_level),
            "MedicationRequestStatus": (
                "Partially fulfilled"
                if unmet
                else "Completed"
            ),
            "SourceSystem": "SYNTHETIC_PHASE1_DEMO"
        })

        new_demand.append(row)

    replacements = []

    # Keep every old row and add the new rows.
    # Only files inside the demo source folder change.
    for source_name, extra_rows in [
        ("sales", new_sales),
        ("demand", new_demand)
    ]:
        path = folder / FILES[source_name]

        temporary = path.with_suffix(
            ".next.csv"
        )

        with (
            path.open(
                encoding="utf-8-sig",
                newline=""
            ) as source,
            temporary.open(
                "w",
                encoding="utf-8",
                newline=""
            ) as destination
        ):
            reader = csv.DictReader(source)

            writer = csv.DictWriter(
                destination,
                fieldnames=reader.fieldnames
            )

            writer.writeheader()

            # Existing records stay.
            writer.writerows(reader)

            # New records are added.
            writer.writerows(extra_rows)

        replacements.append(
            (temporary, path)
        )

    for temporary, path in replacements:
        temporary.replace(path)

    state["completed"].append(
        refresh_number
    )

    state_path.write_text(
        json.dumps(state, indent=2),
        encoding="utf-8"
    )

    summary = {
        "refresh": refresh_number,
        "period": month.strftime("%Y-%m"),
        "new_sales": len(new_sales),
        "new_demand": len(new_demand),
        "new_medicines": 0,
        "seed": 202600 + refresh_number,
        "method": (
            "Template-based synthetic records "
            "with new IDs and dates. "
            "Existing records are retained."
        ),
        "assumptions": [
            "Medicine definitions stay unchanged.",
            (
                f"{sales_count} sales were chosen "
                "for a small visible classroom refresh."
            ),
            (
                "One monthly demand row is generated "
                "for every existing hospital and medicine pair."
            ),
            "Sales discount is 5 percent.",
            "Sales tax is 6 percent of net sales.",
            (
                "Previous hospital closing stock "
                "becomes the next opening stock."
            ),
            (
                "Service level and stockout days "
                "use demonstration rules."
            ),
            (
                "Hospital context and upstream trace references "
                "are reused from templates. "
                "Manufacturing and IoT events are not generated."
            )
        ]
    }

    summary_path = folder / (
        f"refresh_{refresh_number}_method.json"
    )

    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8"
    )

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--prepare",
        action="store_true"
    )

    parser.add_argument(
        "--refresh",
        type=int,
        choices=[1, 2]
    )

    parser.add_argument(
        "--sales",
        type=int,
        default=1000
    )

    arguments = parser.parse_args()

    if arguments.prepare:
        prepare_demo()

    if arguments.refresh:
        generate_refresh(
            arguments.refresh,
            arguments.sales
        )

    if not arguments.prepare and not arguments.refresh:
        parser.print_help()