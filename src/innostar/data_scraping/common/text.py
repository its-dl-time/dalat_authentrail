from __future__ import annotations

import re
from typing import Any

import pandas as pd


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def normalize_text(value: Any) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"[^\w\sÀ-ỹ#.!?%-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value).replace(",", "")))
    except Exception:
        return default


def safe_float(value: Any, default=None):
    try:
        if value is None or value == "":
            return default
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def get_first(item: dict, keys: list[str], default=""):
    for key in keys:
        value = item.get(key)
        if value not in [None, ""]:
            return value
    return default

