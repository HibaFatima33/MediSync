"""Read the small settings file. No source data is changed."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def settings():
    path = Path(os.environ.get("PHARMA_CONFIG", ROOT / "config.json"))
    if not path.exists():
        path = ROOT / "config.example.json"
    cfg = json.loads(path.read_text(encoding="utf-8-sig"))
    for key in ("source_folder", "work_folder", "results_folder"):
        value = Path(cfg[key]).expanduser()
        cfg[key] = value if value.is_absolute() else ROOT / value
    # A connection string may instead be supplied in an environment variable.
    cfg["postgres_dsn"] = os.environ.get("PHARMA_POSTGRES_DSN", cfg.get("postgres_dsn", ""))
    return cfg
