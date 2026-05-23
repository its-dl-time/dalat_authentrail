from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

MAX_TRUST_SCORE = 0.25
MIN_TRUST_SCORE = -0.25

RULE_WEIGHTS = {
    "duplicate_location": -0.10,
    "media_ratio_verified": 0.20,
    "community_interaction": 0.05,
    "geo_verification": 0.05,
    "rating_spike": -0.20,
    "category_specialist": -0.10,
}

MEDIA_COORD_FIELDS = [
    "content_latitude",
    "content_longitude",
    "media_latitude",
    "media_longitude",
    "photo_latitude",
    "photo_longitude",
    "video_latitude",
    "video_longitude",
    "gps_latitude",
    "gps_longitude",
    "gps_lat",
    "gps_lng",
    "lat",
    "lng",
]

MEDIA_COUNT_FIELDS = [
    "media_count",
    "photo_count",
    "video_count",
    "image_count",
    "images_count",
]

MIN_SPECIALIST_RECORDS = 4
MIN_DUPLICATE_REVIEWS = 3
DUPLICATE_WINDOW_DAYS = 30
INTERACTION_AGE_DAYS = 30
GEO_VERIFICATION_METERS = 500


def safe_str(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None or pd.isna(value) or value == "":
        return default
    try:
        if isinstance(value, str):
            return float(value.replace(",", "."))
        return float(value)
    except Exception:
        return default


def parse_datetime(value: Any) -> Optional[pd.Timestamp]:
    value = safe_str(value)
    if not value:
        return None
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return parsed


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
        return float("inf")

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return 6371000.0 * c


def get_record_coordinates(row: pd.Series) -> Tuple[Optional[float], Optional[float]]:
    lat = None
    lng = None

    for f in MEDIA_COORD_FIELDS:
        if f in row:
            value = safe_float(row.get(f))
            if value is not None:
                if "lat" in f and lat is None:
                    lat = value
                elif "lng" in f and lng is None:
                    lng = value
                elif "latitude" in f and lat is None:
                    lat = value
                elif "longitude" in f and lng is None:
                    lng = value

    if lat is not None and lng is not None:
        return lat, lng
    return None, None


def has_media_count(row: pd.Series) -> bool:
    for field in MEDIA_COUNT_FIELDS:
        if field in row and safe_float(row.get(field), 0) > 0:
            return True
    return False


def build_master_lookup(master: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    for _, row in master.iterrows():
        place_id = safe_str(row.get("place_id"))
        if not place_id:
            continue
        lookup[place_id] = {
            "lat": safe_float(row.get("lat")),
            "lng": safe_float(row.get("lng")),
            "category": safe_str(row.get("category")),
        }
    return lookup


def compute_duplicate_location_flags(df: pd.DataFrame) -> pd.Series:
    flags = pd.Series(False, index=df.index)
    df_sorted = df.sort_values(["author_key", "place_id", "record_date"])

    for (_, place_id), group in df_sorted.groupby(["author_key", "place_id"], dropna=False):
        dates = list(group["record_date"])
        indices = list(group.index)
        for i, current_date in enumerate(dates):
            if current_date is None:
                continue
            count = 1
            j = i - 1
            while j >= 0 and dates[j] is not None and (current_date - dates[j]).days <= DUPLICATE_WINDOW_DAYS:
                count += 1
                j -= 1
            if count >= MIN_DUPLICATE_REVIEWS:
                flags.loc[indices[i]] = True

    return flags


def compute_rating_spike_flags(df: pd.DataFrame) -> pd.Series:
    flags = pd.Series(False, index=df.index)
    google_rows = df[df["platform"] == "google_maps"].copy()
    google_rows = google_rows.dropna(subset=["record_date", "rating"])
    google_rows["rating"] = pd.to_numeric(google_rows["rating"], errors="coerce")
    google_rows = google_rows.dropna(subset=["rating"])

    for place_id, group in google_rows.groupby("place_id"):
        group = group.sort_values("record_date")
        ratings = list(group["rating"])
        indices = list(group.index)
        for i in range(2, len(ratings)):
            window = ratings[max(0, i - 2) : i + 1]
            if len(window) < 3:
                continue
            std = float(pd.Series(window).std(ddof=0))
            if std == 0:
                continue
            prev_mean = float(pd.Series(window[:-1]).mean())
            if abs(window[-1] - prev_mean) > std:
                flags.loc[indices[i]] = True

    return flags


def compute_category_specialist_flags(df: pd.DataFrame) -> pd.Series:
    flags = pd.Series(False, index=df.index)
    authors = df["author_key"].fillna("")
    categories = df["place_category"].fillna("unknown")

    for author_key, group in df.groupby(authors):
        if not author_key:
            continue
        total = len(group)
        if total < MIN_SPECIALIST_RECORDS:
            continue
        top_share = group["place_category"].fillna("unknown").value_counts(normalize=True).max()
        if top_share > 0.8:
            flags.loc[group.index] = True

    return flags


def compute_has_media_gps_flags(df: pd.DataFrame) -> pd.Series:
    flags = pd.Series(False, index=df.index)
    for index, row in df.iterrows():
        lat, lng = get_record_coordinates(row)
        if lat is None or lng is None:
            continue
        if not has_media_count(row):
            continue
        flags.loc[index] = True
    return flags


def compute_community_interaction_flags(df: pd.DataFrame) -> pd.Series:
    flags = pd.Series(False, index=df.index)
    now = pd.Timestamp.now(tz=timezone.utc)
    for index, row in df.iterrows():
        engagement = safe_float(row.get("engagement_count"), 0)
        created = row.get("record_date")
        reference = row.get("scraped_date") or now
        if created is None:
            continue
        if engagement <= 0:
            continue
        age = (reference - created).days
        if age >= INTERACTION_AGE_DAYS:
            flags.loc[index] = True
    return flags


def compute_geo_verification_flags(df: pd.DataFrame) -> pd.Series:
    flags = pd.Series(False, index=df.index)
    for index, row in df.iterrows():
        lat, lng = get_record_coordinates(row)
        place_lat = safe_float(row.get("place_lat"))
        place_lng = safe_float(row.get("place_lng"))
        if lat is None or lng is None or place_lat is None or place_lng is None:
            continue
        distance = haversine_distance(lat, lng, place_lat, place_lng)
        if distance <= GEO_VERIFICATION_METERS:
            flags.loc[index] = True
    return flags


def compute_class1_trust_scores(common: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    out = common.copy()
    if "place_id" not in out.columns:
        raise ValueError("Input data must contain place_id")

    master_lookup = build_master_lookup(master)
    out["author_key"] = out["author_id_or_name"].fillna("")
    out["record_date"] = out["content_created_at"].apply(parse_datetime)
    out["scraped_date"] = out["scraped_at"].apply(parse_datetime)
    out["place_category"] = out.get("place_category", "")
    out["place_category"] = out.apply(
        lambda row: row["place_category"]
        if safe_str(row["place_category"]) != ""
        else safe_str(master_lookup.get(safe_str(row["place_id"]), {}).get("category", "")),
        axis=1,
    )
    out["place_lat"] = out.apply(
        lambda row: safe_float(row.get("place_lat"))
        if safe_str(row.get("place_lat")) != ""
        else safe_float(master_lookup.get(safe_str(row.get("place_id")), {}).get("lat")),
        axis=1,
    )
    out["place_lng"] = out.apply(
        lambda row: safe_float(row.get("place_lng"))
        if safe_str(row.get("place_lng")) != ""
        else safe_float(master_lookup.get(safe_str(row.get("place_id")), {}).get("lng")),
        axis=1,
    )

    out["duplicate_location"] = compute_duplicate_location_flags(out)
    out["rating_spike"] = compute_rating_spike_flags(out)
    out["category_specialist"] = compute_category_specialist_flags(out)
    out["media_ratio_verified"] = compute_has_media_gps_flags(out)
    out["community_interaction"] = compute_community_interaction_flags(out)
    out["geo_verification"] = compute_geo_verification_flags(out)

    scores = pd.Series(0.0, index=out.index)
    scores += out["duplicate_location"].astype(float) * RULE_WEIGHTS["duplicate_location"]
    scores += out["rating_spike"].astype(float) * RULE_WEIGHTS["rating_spike"]
    scores += out["category_specialist"].astype(float) * RULE_WEIGHTS["category_specialist"]
    scores += out["media_ratio_verified"].astype(float) * RULE_WEIGHTS["media_ratio_verified"]
    scores += out["community_interaction"].astype(float) * RULE_WEIGHTS["community_interaction"]
    scores += out["geo_verification"].astype(float) * RULE_WEIGHTS["geo_verification"]
    out["trust_score_class1"] = scores.clip(MIN_TRUST_SCORE, MAX_TRUST_SCORE).round(4)

    def build_flag_text(row: pd.Series) -> str:
        active = [key for key in RULE_WEIGHTS if safe_str(row.get(key)) == "True" or row.get(key) is True]
        return "|".join(active)

    out["trust_flags_class1"] = out.apply(build_flag_text, axis=1)
    out["trust_flag_count_class1"] = out["trust_flags_class1"].apply(lambda text: len(text.split("|")) if text else 0)

    for bool_col in [
        "duplicate_location",
        "rating_spike",
        "category_specialist",
        "media_ratio_verified",
        "community_interaction",
        "geo_verification",
    ]:
        if bool_col in out.columns:
            out[bool_col] = out[bool_col].astype(bool)

    return out


def aggregate_place_trust_summary(common: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for place_id, group in common.groupby("place_id"):
        trust_scores = pd.to_numeric(group["trust_score_class1"], errors="coerce").fillna(0)
        rows.append({
            "place_id": place_id,
            "place_name": safe_str(group["place_name"].iloc[0]),
            "record_count": len(group),
            "avg_trust_score_class1": float(trust_scores.mean()) if len(trust_scores) else 0.0,
            "min_trust_score_class1": float(trust_scores.min()) if len(trust_scores) else 0.0,
            "max_trust_score_class1": float(trust_scores.max()) if len(trust_scores) else 0.0,
            "duplicate_location_count": int(group["duplicate_location"].astype(bool).sum()) if "duplicate_location" in group else 0,
            "rating_spike_count": int(group["rating_spike"].astype(bool).sum()) if "rating_spike" in group else 0,
            "category_specialist_count": int(group["category_specialist"].astype(bool).sum()) if "category_specialist" in group else 0,
            "media_ratio_verified_count": int(group["media_ratio_verified"].astype(bool).sum()) if "media_ratio_verified" in group else 0,
            "community_interaction_count": int(group["community_interaction"].astype(bool).sum()) if "community_interaction" in group else 0,
            "geo_verification_count": int(group["geo_verification"].astype(bool).sum()) if "geo_verification" in group else 0,
        })
    return pd.DataFrame(rows).sort_values("place_id").reset_index(drop=True)
