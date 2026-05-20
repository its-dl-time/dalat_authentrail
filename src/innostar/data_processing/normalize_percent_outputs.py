from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CSV_DIR = PROJECT_ROOT / "data" / "processed" / "cross_platform"


def is_percent_string_series(s: pd.Series) -> bool:
    if s.dtype == object:
        sample = s.dropna().astype(str).head(20)
        if sample.empty:
            return False
        return any("%" in x for x in sample)
    return False


def convert_percent_strings(s: pd.Series) -> pd.Series:
    def conv(x):
        if pd.isna(x):
            return x
        t = str(x).strip()
        if t == "":
            return x
        if "%" in t:
            t2 = t.replace("%", "").replace(",", ".")
            try:
                return float(t2) / 100.0
            except Exception:
                return x
        return x

    return s.map(conv)


def convert_numeric_0_100(s: pd.Series) -> pd.Series:
    # only convert if numeric and seems 0-100 range
    try:
        nums = pd.to_numeric(s, errors="coerce")
    except Exception:
        return s
    if nums.dropna().empty:
        return s
    mx = float(nums.max())
    mn = float(nums.min())
    if mx > 1.0 and mx <= 100.0 and mn >= 0.0:
        return (nums / 100.0).round(6)
    return s


def normalize_file(path: Path) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {"converted_columns": [], "skipped": []}
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for col in df.columns:
        ser = df[col]
        if is_percent_string_series(ser):
            df[col] = convert_percent_strings(ser)
            out["converted_columns"].append(col)
            continue
        # try numeric conversion detection
        try:
            nums = pd.to_numeric(ser, errors="coerce")
            if not nums.dropna().empty:
                mx = float(nums.max())
                mn = float(nums.min())
                if mx > 1.0 and mx <= 100.0 and mn >= 0.0:
                    df[col] = (nums / 100.0).round(6)
                    out["converted_columns"].append(col)
                    continue
        except Exception:
            pass
        out["skipped"].append(col)

    # try overwrite file; if not permitted, write to a fallback file with suffix '_normalized'
    try:
        df.to_csv(path, index=False, encoding="utf-8-sig")
        out_path = path
    except PermissionError:
        out_path = path.with_name(path.stem + "_normalized" + path.suffix)
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
    out["out_path"] = str(out_path)
    return out


def main():
    if not CSV_DIR.exists():
        print(f"CSV dir not found: {CSV_DIR}")
        return
    files = sorted([p for p in CSV_DIR.glob("*.csv")])
    if not files:
        print("No CSV files found to normalize.")
        return

    summary = {}
    for f in files:
        print(f"Normalizing: {f.name}")
        res = normalize_file(f)
        summary[f.name] = res

    print("\nNormalization summary:")
    for fname, info in summary.items():
        print(f"- {fname}: converted {len(info['converted_columns'])} columns")
        if info["converted_columns"]:
            print("  converted:", ", ".join(info["converted_columns"]))


if __name__ == "__main__":
    main()
