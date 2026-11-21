"""
synthetic data generator.

Original source files are not edited.
--prepare creates a separate demo copy.
--refresh 1 adds January 2026.
--refresh 2 adds February 2026.
"""

import argparse
import calendar
import csv
import hashlib
import json
import os
import random
import shutil

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from project_settings import ROOT, CONFIG_DIR, settings
from load_csv_to_postgres import FILES
from build_duckdb_tables import lock


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
            CONFIG_DIR / "config.json"
        )
    )

    original_config = (
        config_path
        if config_path.exists()
        else CONFIG_DIR / "config.example.json"
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


def _generate_refresh(refresh_number, sales_count, cfg, request_id=None):
    folder = cfg["source_folder"]
    state_path = folder / "demo_state.json"

    if not state_path.exists():
        raise ValueError(
            "Run generate_demo_records.py --prepare first."
        )

    state = json.loads(
        state_path.read_text(encoding="utf-8")
    )

    if refresh_number in state["completed"]:
        return {
            "status": "already_completed",
            "refresh": refresh_number,
            "period": refresh_month(refresh_number).strftime("%Y-%m"),
            "new_sales": 0,
            "new_demand": 0
        }

    if (
        refresh_number > 1
        and refresh_number - 1 not in state["completed"]
    ):
        raise ValueError(
            "Complete the previous refresh before this one."
        )

    if sales_count < 1:
        raise ValueError(
            "Sales count must be positive."
        )

    month = refresh_month(refresh_number)

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

    state["completed"].append(
        refresh_number
    )

    if request_id:
        state.setdefault("airflow_requests", {})[request_id] = refresh_number

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

    summary_temporary = summary_path.with_suffix(".next.json")
    summary_temporary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    state_temporary = state_path.with_suffix(".next.json")
    state_temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    replacements.extend([(summary_temporary, summary_path), (state_temporary, state_path)])

    # A retry can complete this exact transaction if file publication is interrupted.
    journal = {
        "files": [
            {"temporary": temporary.name, "target": target.name,
             "sha256": file_digest(temporary)}
            for temporary, target in replacements
        ]
    }
    journal_path = folder / "generation.pending.json"
    pending = folder / "generation.pending.next.json"
    pending.write_text(json.dumps(journal, indent=2), encoding="utf-8")
    pending.replace(journal_path)
    publish_generation(folder)
    return {"status": "generated", **summary}


def refresh_month(number):
    if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= 36:
        raise ValueError("Refresh number must be a whole number from 1 to 36.")
    return date(2026 + (number - 1) // 12, (number - 1) % 12 + 1, 1)


def file_digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def publish_generation(folder):
    journal_path = folder / "generation.pending.json"
    if not journal_path.exists():
        return
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    for item in journal["files"]:
        if any(Path(item[key]).name != item[key] for key in ("temporary", "target")):
            raise ValueError("Invalid generation journal path.")
        temporary = folder / item["temporary"]
        target = folder / item["target"]
        candidate = temporary if temporary.exists() else target
        if not candidate.exists() or file_digest(candidate) != item["sha256"]:
            raise ValueError("Generation recovery check failed for " + item["target"])
        if temporary.exists():
            temporary.replace(target)
    journal_path.unlink()


def generate_refresh(refresh_number=None, sales_count=1000, cfg=None, request_id=None):
    cfg = cfg or settings()
    if isinstance(sales_count, bool) or not isinstance(sales_count, int) or sales_count < 1:
        raise ValueError("Sales count must be a positive whole number.")
    if request_id is not None and (not isinstance(request_id, str) or not request_id or len(request_id) > 300):
        raise ValueError("A valid Airflow run ID is required.")
    folder = cfg["source_folder"]
    with lock(cfg):
        publish_generation(folder)
        state_path = folder / "demo_state.json"
        if not state_path.exists():
            raise ValueError("Run generate_demo_records.py --prepare once to set up the separate demo source.")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        completed = state.get("completed", [])
        if completed and sorted(set(completed)) != list(range(1, max(completed) + 1)):
            raise ValueError("Demo refresh history has gaps. Review demo_state.json.")
        previous = state.get("airflow_requests", {}).get(request_id)
        if previous is not None:
            refresh_number = previous
        elif refresh_number is None:
            refresh_number = max(completed, default=0) + 1
        refresh_month(refresh_number)
        return _generate_refresh(refresh_number, sales_count, cfg, request_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--prepare",
        action="store_true"
    )

    parser.add_argument(
        "--refresh",
        type=int
    )

    parser.add_argument(
        "--sales",
        type=int,
        default=1000
    )

    parser.add_argument("--next", action="store_true", help="Generate the next month after the completed history")
    arguments = parser.parse_args()
    if arguments.next and arguments.refresh:
        parser.error("Choose --next or --refresh.")

    if arguments.prepare:
        prepare_demo()

    if arguments.refresh or arguments.next:
        print(json.dumps(generate_refresh(arguments.refresh, arguments.sales), indent=2))

    if not arguments.prepare and not arguments.refresh and not arguments.next:
        parser.print_help()