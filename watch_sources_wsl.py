"""
Watch the three source CSV files.

When a file changes, automatically trigger the
sales_demand_visuals Airflow workflow.

Run this script through Ubuntu's Airflow environment.
It does not change source records.
"""

import argparse
import json
import os
import subprocess
import sys
import time

from pathlib import Path, PureWindowsPath


FILES = (
    "01_master_data.csv",
    "05_pharmacy_sales_data.csv",
    "06_hospital_demand_data.csv"
)


def ubuntu_path(value, base):
    """Convert a Windows path into its Ubuntu WSL path."""

    windows_path = PureWindowsPath(str(value))

    if (
        windows_path.drive
        and len(windows_path.drive) == 2
        and windows_path.drive[1] == ":"
    ):
        drive = windows_path.drive[0].lower()

        return (
            Path("/mnt")
            / drive
            / Path(*windows_path.parts[1:])
        )

    path = Path(value).expanduser()

    return path if path.is_absolute() else base / path


def file_details(folder):
    """Read each file's size and modification time."""

    return tuple(
        (
            name,
            (folder / name).stat().st_size,
            (folder / name).stat().st_mtime_ns
        )
        for name in FILES
    )


def watch(config_path, dag_id, once=False):
    config_path = Path(config_path).resolve()

    config = json.loads(
        config_path.read_text(encoding="utf-8-sig")
    )

    source_folder = ubuntu_path(
        config["source_folder"],
        config_path.parent
    )

    airflow_command = (
        Path(sys.executable).parent / "airflow"
    )

    if not airflow_command.exists():
        raise RuntimeError(
            "Use Ubuntu's Airflow Python environment "
            "to run this watcher."
        )

    environment = os.environ.copy()

    environment.setdefault(
        "AIRFLOW_HOME",
        str(Path.home() / "airflow")
    )

    previous = file_details(source_folder)

    print(
        "Watching:",
        source_folder,
        flush=True
    )

    print(
        "Waiting for a changed file.",
        flush=True
    )

    while True:
        try:
            time.sleep(5)

            current = file_details(source_folder)

            if current == previous:
                continue

            # Check again to avoid reading a file
            # while it is still being copied.
            time.sleep(5)

            if file_details(source_folder) != current:
                continue

            changed_files = [
                new[0]
                for new, old in zip(current, previous)
                if new != old
            ]

            print(
                "Detected changes:",
                ", ".join(changed_files),
                flush=True
            )

            result = subprocess.run(
                [
                    str(airflow_command),
                    "dags",
                    "trigger",
                    dag_id
                ],
                env=environment,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                print(
                    "Airflow did not accept the run.",
                    result.stdout,
                    result.stderr,
                    flush=True
                )

                continue

            previous = current

            print(result.stdout, flush=True)

            print(
                "Airflow run requested automatically.",
                flush=True
            )

            if once:
                return

        except FileNotFoundError:
            print(
                "Waiting for a source file "
                "to finish copying.",
                flush=True
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        required=True
    )

    parser.add_argument(
        "--dag",
        default="sales_demand_visuals"
    )

    parser.add_argument(
        "--once",
        action="store_true"
    )

    arguments = parser.parse_args()

    try:
        watch(
            arguments.config,
            arguments.dag,
            arguments.once
        )

    except KeyboardInterrupt:
        print("\nWatcher stopped.")