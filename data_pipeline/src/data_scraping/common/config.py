from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[4]
PIPELINE_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PIPELINE_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
OUTPUTS_DIR = DATA_DIR / "outputs"
PROCESSED_DIR = DATA_DIR / "processed"
MASTER_PLACES_FILE = PROCESSED_DIR / "places_master_top50.csv"


def load_apify_token(required: bool = True) -> str:
    load_dotenv(PROJECT_ROOT / ".env")
    token = os.getenv("APIFY_TOKEN", "").strip()
    if required and not token:
        raise ValueError("Missing APIFY_TOKEN in .env")
    return token


def make_run_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
