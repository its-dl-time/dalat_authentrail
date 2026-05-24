from __future__ import annotations

import math
from datetime import timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

MAX_LAYER1_SCORE = 0.20
MIN_LAYER1_SCORE = -0.35

# rating_spike is NOT in this dict — its penalty is conditional on text length
RULE_WEIGHTS = {
    "layer1_duplicate_location": -0.10,
    "layer1_media_gps_verified": 0.10,
    "layer1_community_interaction": 0.05,
    "layer1_geo_verified": 0.05,
    "layer1_category_specialist": -0.10,
}

# Rating spike penalty varies by whether the review has meaningful text
RATING_SPIKE_PENALTY_NO_TEXT = -0.15   # spike + no text → harshest
RATING_SPIKE_PENALTY_WITH_TEXT = -0.05  # spike + long text → lighter
SPIKE_TEXT_WORD_THRESHOLD = 8           # "has text" means ≥8 words

MEDIA_COORD_FIELDS = [
    "content_latitude", "content_longitude",
    "media_latitude", "media_longitude",
    "photo_latitude", "photo_longitude",
    "video_latitude", "video_longitude",
    "gps_latitude", "gps_longitude",
    "gps_lat", "gps_lng",
    "lat", "lng",
]

MEDIA_COUNT_FIELDS = [
    "media_count", "photo_count", "video_count", "image_count", "images_count",
]

MIN_SPECIALIST_RECORDS = 4
MIN_DUPLICATE_REVIEWS = 3
DUPLICATE_WINDOW_DAYS = 30
INTERACTION_AGE_DAYS = 30
GEO_VERIFICATION_METERS = 500

# Rating spike: require 5-review window, ≥2-star absolute deviation, AND std ≥ 1.0
# so that a place consistently getting 5-stars is never flagged
RATING_SPIKE_MIN_REVIEWS = 5
RATING_SPIKE_WINDOW = 5
RATING_SPIKE_MIN_DEVIATION = 2.0
RATING_SPIKE_MIN_STD = 1.0


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
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
        if len(ratings) < RATING_SPIKE_MIN_REVIEWS:
            continue
        for i in range(RATING_SPIKE_WINDOW - 1, len(ratings)):
            window = ratings[max(0, i - RATING_SPIKE_WINDOW + 1): i + 1]
            if len(window) < RATING_SPIKE_WINDOW:
                continue
            current = window[-1]
            prev_mean = float(pd.Series(window[:-1]).mean())
            std = float(pd.Series(window).std(ddof=0))
            # Only flag genuine anomalies: ≥2 star deviation AND meaningful variance
            if abs(current - prev_mean) >= RATING_SPIKE_MIN_DEVIATION and std >= RATING_SPIKE_MIN_STD:
                flags.loc[indices[i]] = True
    return flags


def compute_category_specialist_flags(df: pd.DataFrame) -> pd.Series:
    flags = pd.Series(False, index=df.index)
    authors = df["author_key"].fillna("")
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


def compute_layer1_behavior_scores(common: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
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

    out["layer1_duplicate_location"] = compute_duplicate_location_flags(out)
    out["layer1_rating_spike"] = compute_rating_spike_flags(out)
    out["layer1_category_specialist"] = compute_category_specialist_flags(out)
    out["layer1_media_gps_verified"] = compute_has_media_gps_flags(out)
    out["layer1_community_interaction"] = compute_community_interaction_flags(out)
    out["layer1_geo_verified"] = compute_geo_verification_flags(out)

    scores = pd.Series(0.0, index=out.index)
    for flag_col, weight in RULE_WEIGHTS.items():
        scores += out[flag_col].astype(float) * weight

    # Rating spike penalty is conditional on whether the review has meaningful text
    word_counts = out["content_text"].apply(
        lambda t: len(str(t).split()) if pd.notna(t) and str(t).strip() else 0
    )
    spike = out["layer1_rating_spike"].astype(bool)
    scores += (spike & (word_counts < SPIKE_TEXT_WORD_THRESHOLD)).astype(float) * RATING_SPIKE_PENALTY_NO_TEXT
    scores += (spike & (word_counts >= SPIKE_TEXT_WORD_THRESHOLD)).astype(float) * RATING_SPIKE_PENALTY_WITH_TEXT

    out["trust_score_layer1"] = scores.clip(MIN_LAYER1_SCORE, MAX_LAYER1_SCORE).round(4)

    all_flag_cols = list(RULE_WEIGHTS.keys()) + ["layer1_rating_spike"]

    def build_flag_text(row: pd.Series) -> str:
        active = [key for key in all_flag_cols if row.get(key) is True]
        return "|".join(active)

    out["trust_flags_layer1"] = out.apply(build_flag_text, axis=1)
    out["trust_flag_count_layer1"] = out["trust_flags_layer1"].apply(
        lambda text: len([f for f in text.split("|") if f]) if text else 0
    )

    for bool_col in all_flag_cols:
        if bool_col in out.columns:
            out[bool_col] = out[bool_col].astype(bool)

    return out


def aggregate_place_trust_summary(common: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for place_id, group in common.groupby("place_id"):
        trust_scores = pd.to_numeric(group["trust_score_layer1"], errors="coerce").fillna(0)
        rows.append({
            "place_id": place_id,
            "place_name": safe_str(group["place_name"].iloc[0]),
            "record_count": len(group),
            "avg_trust_score_layer1": round(float(trust_scores.mean()), 4) if len(trust_scores) else 0.0,
            "min_trust_score_layer1": round(float(trust_scores.min()), 4) if len(trust_scores) else 0.0,
            "max_trust_score_layer1": round(float(trust_scores.max()), 4) if len(trust_scores) else 0.0,
            "duplicate_location_count": int(group["layer1_duplicate_location"].astype(bool).sum()) if "layer1_duplicate_location" in group else 0,
            "rating_spike_count": int(group["layer1_rating_spike"].astype(bool).sum()) if "layer1_rating_spike" in group else 0,
            "category_specialist_count": int(group["layer1_category_specialist"].astype(bool).sum()) if "layer1_category_specialist" in group else 0,
            "media_gps_verified_count": int(group["layer1_media_gps_verified"].astype(bool).sum()) if "layer1_media_gps_verified" in group else 0,
            "community_interaction_count": int(group["layer1_community_interaction"].astype(bool).sum()) if "layer1_community_interaction" in group else 0,
            "geo_verified_count": int(group["layer1_geo_verified"].astype(bool).sum()) if "layer1_geo_verified" in group else 0,
        })
    return pd.DataFrame(rows).sort_values("place_id").reset_index(drop=True)
