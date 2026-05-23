from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd


def read_existing_csv(path: Path | str) -> pd.DataFrame:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception:
        return pd.DataFrame()


def save_csv(
    df: pd.DataFrame,
    path: Path | str,
    append: bool = False,
    dedupe_subset: list[str] | None = None,
) -> pd.DataFrame:
    path = Path(path)
    if append:
        old = read_existing_csv(path)
        if len(old) > 0:
            df = pd.concat([old, df], ignore_index=True)

    if len(df) > 0 and dedupe_subset:
        available = [col for col in dedupe_subset if col in df.columns]
        if available:
            df = df.drop_duplicates(subset=available, keep="last")

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return df


def append_jsonl(rows: Iterable[dict], path: Path | str) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            count += 1
    return count


def read_jsonl(path: Path | str) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def read_jsonl_dir(directory: Path | str, pattern: str = "*.jsonl") -> list[dict]:
    directory = Path(directory)
    rows: list[dict] = []
    if not directory.exists():
        return rows
    for path in sorted(directory.glob(pattern)):
        rows.extend(read_jsonl(path))
    return rows


def read_master_places(path: Path | str) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)

