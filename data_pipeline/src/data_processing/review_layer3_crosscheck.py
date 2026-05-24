from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

MAX_LAYER3_SCORE = 0.21
MIN_LAYER3_SCORE = -0.73

TOPIC_COLUMNS = [
    "service_score", "price_score", "scenery_score",
    "crowded_score", "food_drink_score", "cleanliness_score", "location_score",
]

TOPIC_ACTIVE_THRESHOLD = 0.10
SENTIMENT_HIGH_GAP = 0.60      # tighter than before (was 0.50)
SENTIMENT_LOW_GAP = 0.20
RATING_HIGH_GAP = 1.5
RATING_CONSISTENT_MAX = 0.50
PLATFORM_SENTIMENT_GAP = 0.30
TOPIC_OVERLAP_HIGH = 0.60      # ratio above which → bonus
TOPIC_OVERLAP_LOW = 0.40       # ratio below which → penalty
ENGAGEMENT_OUTLIER_THRESHOLD = 0.90  # top 10% engagement → suspicious in uncertain zone
TEMPORAL_SPIKE_RATIO = 0.40    # >40% reviews from same month → temporal anomaly


def safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def build_place_baselines(common: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    baselines: Dict[str, Dict[str, Any]] = {}
    for place_id, group in common.groupby("place_id"):
        sentiment = pd.to_numeric(group["sentiment_score"], errors="coerce").fillna(0)
        ratings = pd.to_numeric(group["rating"], errors="coerce")
        ratings = ratings[ratings > 0]

        topic_avgs: Dict[str, float] = {}
        dominant_topics: List[str] = []
        for topic in TOPIC_COLUMNS:
            if topic in group.columns:
                vals = pd.to_numeric(group[topic], errors="coerce").fillna(0)
                avg = float(vals.mean())
                topic_avgs[topic] = avg
                if avg >= TOPIC_ACTIVE_THRESHOLD:
                    dominant_topics.append(topic)

        baselines[str(place_id)] = {
            "avg_sentiment": float(sentiment.mean()),
            "avg_rating": float(ratings.mean()) if len(ratings) else 0.0,
            "dominant_topics": dominant_topics,
            **{f"avg_{t}": topic_avgs.get(t, 0.0) for t in TOPIC_COLUMNS},
        }
    return baselines


def build_platform_sentiment_map(common: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    result: Dict[str, Dict[str, float]] = {}
    for (place_id, platform), group in common.groupby(["place_id", "platform"], dropna=False):
        sentiment = pd.to_numeric(group["sentiment_score"], errors="coerce").fillna(0)
        result.setdefault(str(place_id), {})[str(platform)] = float(sentiment.mean())
    return result


def build_temporal_spike_map(common: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """For each (place_id, platform): ratio of reviews that fall in the most common month."""
    result: Dict[str, Dict[str, float]] = {}
    for (place_id, platform), group in common.groupby(["place_id", "platform"], dropna=False):
        dates = pd.to_datetime(group["content_created_at"], errors="coerce", utc=True)
        valid = dates.dropna()
        if len(valid) == 0:
            result.setdefault(str(place_id), {})[str(platform)] = 0.0
            continue
        month_counts = valid.dt.tz_convert(None).dt.to_period("M").value_counts()
        top_ratio = float(month_counts.iloc[0]) / len(valid)
        result.setdefault(str(place_id), {})[str(platform)] = round(top_ratio, 4)
    return result


def compute_layer3_crosscheck_scores(common: pd.DataFrame) -> pd.DataFrame:
    out = common.copy()

    out["crosscheck_applied"] = False
    out["crosscheck_sentiment_gap"] = 0.0
    out["crosscheck_rating_gap"] = 0.0
    out["crosscheck_topic_overlap_ratio"] = 0.0
    out["crosscheck_platform_gap"] = False
    out["crosscheck_engagement_percentile"] = 0.0
    out["crosscheck_temporal_spike"] = False
    out["trust_score_layer3"] = 0.0
    out["trust_flags_layer3"] = ""
    out["trust_flag_count_layer3"] = 0

    baselines = build_place_baselines(out)
    platform_sentiments = build_platform_sentiment_map(out)
    temporal_spikes = build_temporal_spike_map(out)

    for idx, row in out.iterrows():
        place_id = safe_str(row.get("place_id", ""))
        platform = safe_str(row.get("platform", ""))
        baseline = baselines.get(place_id)
        if not baseline:
            continue

        out.at[idx, "crosscheck_applied"] = True

        # --- Sentiment consistency ---
        review_sentiment = safe_float(row.get("sentiment_score"), 0.0)
        sentiment_gap = round(abs(review_sentiment - baseline["avg_sentiment"]), 4)
        out.at[idx, "crosscheck_sentiment_gap"] = sentiment_gap

        # --- Rating consistency ---
        review_rating = safe_float(row.get("rating"), 0.0)
        rating_gap = 0.0
        if review_rating > 0 and baseline["avg_rating"] > 0:
            rating_gap = round(abs(review_rating - baseline["avg_rating"]), 4)
        out.at[idx, "crosscheck_rating_gap"] = rating_gap

        # --- Topic overlap ratio ---
        dominant = baseline.get("dominant_topics", [])
        review_topics = [t for t in TOPIC_COLUMNS if safe_float(row.get(t), 0.0) >= TOPIC_ACTIVE_THRESHOLD]
        if dominant:
            overlap_ratio = round(len(set(review_topics) & set(dominant)) / len(dominant), 4)
        else:
            overlap_ratio = 1.0 if review_topics else 0.0
        out.at[idx, "crosscheck_topic_overlap_ratio"] = overlap_ratio

        # --- Platform sentiment gap ---
        platform_sents = platform_sentiments.get(place_id, {})
        other_sents = [v for k, v in platform_sents.items() if k != platform]
        platform_gap = False
        if other_sents:
            my_sent = platform_sents.get(platform, review_sentiment)
            avg_others = sum(other_sents) / len(other_sents)
            platform_gap = (avg_others - my_sent) > PLATFORM_SENTIMENT_GAP
        out.at[idx, "crosscheck_platform_gap"] = platform_gap

        # --- Engagement outlier ---
        engagement_pct = safe_float(row.get("normalized_engagement"), 0.0)
        out.at[idx, "crosscheck_engagement_percentile"] = engagement_pct

        # --- Temporal spike ---
        spike_ratio = temporal_spikes.get(place_id, {}).get(platform, 0.0)
        temporal_spike = spike_ratio >= TEMPORAL_SPIKE_RATIO
        out.at[idx, "crosscheck_temporal_spike"] = temporal_spike

        # --- Context signals ---
        word_count = int(safe_float(row.get("nlp_word_count"), 0))
        layer2_flags = safe_str(row.get("trust_flags_layer2", ""))
        has_credible_negative = "credible_negative" in layer2_flags
        lang = safe_str(row.get("language", "")).lower()
        is_vi_or_en = lang in {"vi", "en", ""}

        # --- Compute Layer 3 score ---
        score = 0.0
        flags: List[str] = []

        # BONUSES — only for reviews with enough text to be meaningful
        if word_count >= 10:
            if sentiment_gap < SENTIMENT_LOW_GAP:
                score += 0.08
                flags.append("sentiment_consistent")
            if 0 < rating_gap <= RATING_CONSISTENT_MAX:
                score += 0.08
                flags.append("rating_consistent")
            if overlap_ratio >= TOPIC_OVERLAP_HIGH:
                score += 0.05
                flags.append("topic_consistent")

        # PENALTIES
        # credible_negative reviews legitimately deviate from a positive baseline — skip penalty
        if sentiment_gap > SENTIMENT_HIGH_GAP and not has_credible_negative:
            score -= 0.15
            flags.append("high_sentiment_deviation")
        if rating_gap > RATING_HIGH_GAP:
            score -= 0.15
            flags.append("high_rating_deviation")
        # topic matching is keyword-based (vi/en) — skip for other languages
        if overlap_ratio < TOPIC_OVERLAP_LOW and dominant and is_vi_or_en:
            score -= 0.10
            flags.append("low_topic_overlap")
        if platform_gap:
            score -= 0.15
            flags.append("platform_sentiment_gap")
        if engagement_pct > ENGAGEMENT_OUTLIER_THRESHOLD:
            score -= 0.08
            flags.append("engagement_outlier")
        if temporal_spike:
            score -= 0.10
            flags.append("temporal_spike")

        score = round(max(MIN_LAYER3_SCORE, min(MAX_LAYER3_SCORE, score)), 4)

        out.at[idx, "trust_score_layer3"] = score
        out.at[idx, "trust_flags_layer3"] = "|".join(flags)
        out.at[idx, "trust_flag_count_layer3"] = len(flags)

    return out
