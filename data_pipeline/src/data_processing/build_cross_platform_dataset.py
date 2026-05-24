import argparse
import hashlib
import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

import pandas as pd

try:
    from dotenv import load_dotenv as _load_dotenv

    _load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)
except Exception:
    pass

try:
    from .review_layer1_behavior import (
        aggregate_place_trust_summary,
        compute_layer1_behavior_scores,
    )
    from .review_layer2_nlp import compute_layer2_nlp_scores
    from .review_layer3_crosscheck import compute_layer3_crosscheck_scores
    from .review_translation import add_translation_normalization
except ImportError:
    from review_layer1_behavior import (
        aggregate_place_trust_summary,
        compute_layer1_behavior_scores,
    )
    from review_layer2_nlp import compute_layer2_nlp_scores
    from review_layer3_crosscheck import compute_layer3_crosscheck_scores
    from review_translation import add_translation_normalization

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PIPELINE_ROOT / "data"

MASTER_PLACES_FILE = DATA_DIR / "processed" / "places_master_top50.csv"
GOOGLE_MAPS_FILE = DATA_DIR / "outputs" / "google_maps" / "google_maps_reviews_output.csv"
TIKTOK_FILE = DATA_DIR / "outputs" / "tiktok" / "tiktok_comments_output.csv"
FACEBOOK_FILE = DATA_DIR / "outputs" / "facebook" / "facebook_comments_output.csv"

OUTPUT_DIR = DATA_DIR / "processed" / "cross_platform"

COMMON_OUTPUT_FILE = OUTPUT_DIR / "normalized_common_records.csv"
GOOGLE_FEATURES_FILE = OUTPUT_DIR / "platform_google_maps_features.csv"
TIKTOK_FEATURES_FILE = OUTPUT_DIR / "platform_tiktok_features.csv"
FACEBOOK_FEATURES_FILE = OUTPUT_DIR / "platform_facebook_features.csv"
SUMMARY_OUTPUT_FILE = OUTPUT_DIR / "place_platform_summary.csv"
RISK_OUTPUT_FILE = OUTPUT_DIR / "place_cross_platform_risk.csv"
TRUST_OUTPUT_FILE = OUTPUT_DIR / "place_review_trust_summary.csv"
WEIGHTED_RATING_FILE = OUTPUT_DIR / "place_weighted_rating.csv"
CLEAN_ALL_FILE = OUTPUT_DIR / "clean_trusted_records.csv"
CLEAN_GOOGLE_MAPS_FILE = OUTPUT_DIR / "clean_google_maps_reviews.csv"
CLEAN_SOCIAL_REVIEWS_FILE = OUTPUT_DIR / "clean_social_review_signals.csv"
CLEAN_SOCIAL_ENGAGEMENT_FILE = OUTPUT_DIR / "clean_social_engagement_signals.csv"
FILTERING_SUMMARY_FILE = OUTPUT_DIR / "filtering_quality_summary.csv"
TRANSLATION_CACHE_FILE = OUTPUT_DIR / "translation_cache.csv"

REQUIRED_PLATFORMS = ["google_maps", "tiktok", "facebook"]

TOPIC_COLUMNS = [
    "service_score",
    "price_score",
    "scenery_score",
    "crowded_score",
    "food_drink_score",
    "cleanliness_score",
    "location_score",
]

COMMON_COLUMNS = [
    "normalized_id",
    "place_id",
    "place_name",
    "place_category",
    "platform",
    "source_record_id",
    "content_text",
    "rating",
    "content_created_at",
    "author_id_or_name",
    "engagement_count",
    "normalized_engagement",
    "language",
    "quality_score",
    "is_useful",
    "sentiment_score",
    "content_latitude",
    "content_longitude",
    "media_latitude",
    "media_longitude",
    "photo_count",
    "video_count",
    "image_count",
    "media_count",
    *TOPIC_COLUMNS,
    "risk_flags",
    "risk_flag_count",
    "has_risk_flag",
    "scraped_at",
]

POSITIVE_TERMS = [
    "tuyet", "tuyệt", "dep", "đẹp", "ngon", "tot", "tốt", "hay", "ok",
    "on", "ổn", "thich", "thích", "recommend", "recommended", "perfect",
    "great", "good", "nice", "beautiful", "love", "xuat sac", "xuất sắc",
    "de thuong", "dễ thương", "than thien", "thân thiện", "hai long",
    "hài lòng", "dang tien", "đáng tiền", "chill", "thoang", "thoáng",
]

NEGATIVE_TERMS = [
    "te", "tệ", "do", "dở", "chan", "chán", "khong ngon", "không ngon",
    "khong dep", "không đẹp", "that vong", "thất vọng", "bad", "poor",
    "terrible", "awful", "expensive", "dat", "đắt", "mac", "mắc",
    "lau", "lâu", "cho doi", "chờ đợi", "dong", "đông", "on ao", "ồn ào",
    "ban", "bẩn", "khong sach", "không sạch", "thai do", "thái độ",
    "kho chiu", "khó chịu", "lua dao", "lừa đảo", "chem", "chém",
]

SEEDING_TERMS = [
    "uy tin", "uy tín", "chat luong vuot troi", "chất lượng vượt trội",
    "gia ca hop ly", "giá cả hợp lý", "nhanh tay", "inbox", "ib",
    "sale", "voucher", "khuyen mai", "khuyến mãi", "cam ket", "cam kết",
    "dich vu hang dau", "dịch vụ hàng đầu",
]

TOPIC_TERMS = {
    "service_score": [
        "nhan vien", "nhân viên", "phuc vu", "phục vụ", "thai do", "thái độ",
        "service", "staff", "chu quan", "chủ quán", "order",
    ],
    "price_score": [
        "gia", "giá", "dat", "đắt", "re", "rẻ", "mac", "mắc", "price",
        "cost", "dong", "đồng", "k", "vnd",
    ],
    "scenery_score": [
        "view", "canh", "cảnh", "doi", "đồi", "thung lung", "thung lũng",
        "ho", "hồ", "song", "sông", "checkin", "check-in", "khung canh",
        "khung cảnh", "scenery", "landscape",
    ],
    "crowded_score": [
        "dong", "đông", "chen", "chật", "cho lau", "chờ lâu", "xep hang",
        "xếp hàng", "queue", "crowded", "full ban", "full bàn",
    ],
    "food_drink_score": [
        "mon", "món", "do an", "đồ ăn", "nuoc", "nước", "cafe", "coffee",
        "ca phe", "cà phê", "tra", "trà", "banh", "bánh", "ga", "gà",
        "sushi", "egg coffee", "taste", "drink", "food",
    ],
    "cleanliness_score": [
        "sach", "sạch", "ban", "bẩn", "ve sinh", "vệ sinh", "mùi",
        "toilet", "restroom", "clean", "dirty",
    ],
    "location_score": [
        "dia chi", "địa chỉ", "duong", "đường", "gan", "gần", "xa",
        "de di", "dễ đi", "kho di", "khó đi", "parking", "giu xe",
        "giữ xe", "ben xe", "bến xe", "location",
    ],
}


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def safe_float(value: Any, default: float = 0.0) -> float:
    text = safe_str(value)
    if not text:
        return default
    try:
        return float(text.replace(",", "."))
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    text = safe_str(value)
    if not text:
        return default
    try:
        return int(float(text.replace(",", "")))
    except Exception:
        return default


def safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return safe_str(value).lower() in {"1", "true", "yes", "y"}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def clean_text(value: Any) -> str:
    text = safe_str(value)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_text(value: Any) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"[^\w\sÀ-ỹ#.!?%-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def make_id(*parts: Any) -> str:
    raw = "|".join(safe_str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_datetime(value: Any) -> str:
    text = safe_str(value)
    if not text:
        return ""
    parsed = pd.to_datetime(text, errors="coerce", utc=True)
    if pd.isna(parsed):
        return text
    return parsed.isoformat()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def split_flags(flags: Any) -> List[str]:
    text = safe_str(flags)
    if not text:
        return []
    return [flag for flag in text.split("|") if flag]


def count_words(text: str) -> int:
    normalized = normalize_text(text)
    if not normalized:
        return 0
    return len(normalized.split())


def text_has_any(normalized_text: str, terms: Sequence[str]) -> bool:
    return any(term in normalized_text for term in terms)


def count_term_matches(normalized_text: str, terms: Sequence[str]) -> int:
    return sum(1 for term in terms if term in normalized_text)


def count_emoji_like(text: str) -> int:
    return len(
        re.findall(
            "[\U0001F300-\U0001FAFF\U00002700-\U000027BF]",
            safe_str(text),
        )
    )


def emoji_ratio(text: str) -> float:
    text = safe_str(text)
    if not text:
        return 0.0
    return count_emoji_like(text) / max(len(text), 1)


def compute_sentiment(text: str, rating: Optional[float] = None) -> float:
    normalized = normalize_text(text)
    positive = count_term_matches(normalized, POSITIVE_TERMS)
    negative = count_term_matches(normalized, NEGATIVE_TERMS)

    if positive == 0 and negative == 0:
        score = 0.0
    else:
        score = (positive - negative) / max(positive + negative, 1)

    if rating is not None and rating > 0:
        rating_signal = clamp((rating - 3.0) / 2.0, -1.0, 1.0)
        if score == 0:
            score = rating_signal * 0.6
        else:
            score = (score * 0.7) + (rating_signal * 0.3)

    return round(clamp(score, -1.0, 1.0), 4)


def compute_topic_scores(text: str) -> Dict[str, float]:
    normalized = normalize_text(text)
    scores: Dict[str, float] = {}
    for topic, terms in TOPIC_TERMS.items():
        matches = count_term_matches(normalized, terms)
        scores[topic] = round(clamp(matches / 3.0), 4)
    return scores


def compute_google_quality(row: pd.Series) -> float:
    text = clean_text(row.get("review_text", ""))
    words = count_words(text)
    rating = safe_float(row.get("rating"), 0.0)
    reviewer_reviews = safe_int(row.get("reviewer_number_of_reviews"), 0)
    is_local_guide = safe_bool(row.get("is_local_guide"))
    has_owner_response = bool(clean_text(row.get("owner_response_text", "")))

    score = 0.0
    if words >= 8:
        score += 0.35
    elif words >= 3:
        score += 0.18
    if rating > 0:
        score += 0.2
    if reviewer_reviews >= 20:
        score += 0.2
    elif reviewer_reviews > 0:
        score += 0.1
    if is_local_guide:
        score += 0.15
    if has_owner_response:
        score += 0.1
    return round(clamp(score), 4)


def build_risk_flags(
    text: str,
    quality_score: float,
    platform: str,
    spam_signal: bool = False,
    reject_reason: str = "",
    explicit_emoji_ratio: Optional[float] = None,
) -> List[str]:
    flags: List[str] = []
    normalized = normalize_text(text)
    words = count_words(text)
    ratio = explicit_emoji_ratio if explicit_emoji_ratio is not None else emoji_ratio(text)

    if not normalized:
        flags.append("empty_text")
    elif words < 3:
        flags.append("too_short")

    if ratio > 0.2:
        flags.append("emoji_heavy")

    if "#" in safe_str(text) or text_has_any(normalized, SEEDING_TERMS):
        flags.append("seeding_or_promo_language")

    if quality_score < 0.2:
        flags.append("low_quality")

    if spam_signal:
        flags.append("likely_spam")

    if reject_reason and reject_reason not in {"", "nan", "none"}:
        flags.append(f"reject_{reject_reason}")

    if platform == "google_maps" and words == 0:
        flags.append("rating_without_text")

    return sorted(set(flags))


def get_complete_place_ids(frames: Dict[str, pd.DataFrame], master: pd.DataFrame) -> List[str]:
    platform_sets: List[Set[str]] = []
    for platform in REQUIRED_PLATFORMS:
        place_ids = set(frames[platform]["place_id"].map(safe_str))
        platform_sets.append(place_ids)

    complete = set.intersection(*platform_sets)
    master_ids = set(master["place_id"].map(safe_str))
    return sorted(complete.intersection(master_ids))


def prepare_frame(df: pd.DataFrame, place_ids: Sequence[str]) -> pd.DataFrame:
    out = df.copy()
    if "id" in out.columns:
        out = out.drop_duplicates(subset=["id"], keep="last")
    out["place_id"] = out["place_id"].map(safe_str)
    return out[out["place_id"].isin(place_ids)].copy()


def normalize_google_maps(df: pd.DataFrame, master: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    common_rows: List[Dict[str, Any]] = []
    feature_rows: List[Dict[str, Any]] = []
    master_lookup = master.set_index("place_id").to_dict(orient="index")

    for _, row in df.iterrows():
        place_id = safe_str(row.get("place_id"))
        source_id = safe_str(row.get("id")) or safe_str(row.get("review_id"))
        text = clean_text(row.get("review_text"))
        rating = safe_float(row.get("rating"), 0.0)
        quality = compute_google_quality(row)
        sentiment = compute_sentiment(text, rating=rating if rating > 0 else None)
        topics = compute_topic_scores(text)
        flags = build_risk_flags(text, quality, "google_maps")

        common_rows.append({
            "normalized_id": make_id("google_maps", source_id),
            "place_id": place_id,
            "place_name": safe_str(row.get("place_name")) or safe_str(master_lookup.get(place_id, {}).get("title")),
            "platform": "google_maps",
            "source_record_id": source_id,
            "content_text": text,
            "content_created_at": normalize_datetime(row.get("published_at")),
            "author_id_or_name": safe_str(row.get("reviewer_id")) or safe_str(row.get("reviewer_name")),
            "engagement_count": safe_int(row.get("likes_count"), 0),
            "rating": rating,
            "language": "",
            "quality_score": quality,
            "is_useful": quality >= 0.35,
            "sentiment_score": sentiment,
            "place_category": safe_str(row.get("place_category")) or safe_str(master_lookup.get(place_id, {}).get("category")),
            "content_latitude": safe_float(row.get("content_latitude")),
            "content_longitude": safe_float(row.get("content_longitude")),
            "media_latitude": safe_float(row.get("media_latitude")),
            "media_longitude": safe_float(row.get("media_longitude")),
            "photo_count": safe_int(row.get("photo_count"), 0),
            "video_count": safe_int(row.get("video_count"), 0),
            "image_count": safe_int(row.get("image_count"), 0),
            "media_count": safe_int(row.get("media_count"), 0),
            **topics,
            "risk_flags": "|".join(flags),
            "risk_flag_count": len(flags),
            "has_risk_flag": bool(flags),
            "scraped_at": normalize_datetime(row.get("scraped_at")),
        })

        feature_rows.append({
            "source_record_id": source_id,
            "place_id": place_id,
            "platform": "google_maps",
            "rating": rating,
            "review_id": safe_str(row.get("review_id")),
            "review_url": safe_str(row.get("review_url")),
            "reviewer_name": safe_str(row.get("reviewer_name")),
            "reviewer_id": safe_str(row.get("reviewer_id")),
            "reviewer_url": safe_str(row.get("reviewer_url")),
            "reviewer_number_of_reviews": safe_int(row.get("reviewer_number_of_reviews"), 0),
            "is_local_guide": safe_bool(row.get("is_local_guide")),
            "likes_count": safe_int(row.get("likes_count"), 0),
            "owner_response_text": clean_text(row.get("owner_response_text")),
            "owner_response_date": normalize_datetime(row.get("owner_response_date")),
            "google_maps_url": safe_str(row.get("google_maps_url")),
        })

    return pd.DataFrame(common_rows), pd.DataFrame(feature_rows)


def normalize_tiktok(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    common_rows: List[Dict[str, Any]] = []
    feature_rows: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        source_id = safe_str(row.get("id")) or safe_str(row.get("comment_id"))
        text = clean_text(row.get("comment_text"))
        quality = safe_float(row.get("comment_text_quality_score"), 0.0)
        sentiment = compute_sentiment(text)
        topics = compute_topic_scores(text)
        explicit_ratio = safe_float(row.get("comment_emoji_ratio"), emoji_ratio(text))
        flags = build_risk_flags(
            text,
            quality,
            "tiktok",
            spam_signal=safe_bool(row.get("comment_is_likely_spam")),
            explicit_emoji_ratio=explicit_ratio,
        )

        common_rows.append({
            "normalized_id": make_id("tiktok", source_id),
            "place_id": safe_str(row.get("place_id")),
            "place_name": safe_str(row.get("place_name")),
            "platform": "tiktok",
            "source_record_id": source_id,
            "content_text": text,
            "rating": 0.0,
            "content_created_at": normalize_datetime(row.get("comment_created_at")),
            "author_id_or_name": safe_str(row.get("comment_author")),
            "engagement_count": safe_int(row.get("comment_likes"), 0),
            "language": safe_str(row.get("comment_language")),
            "quality_score": quality,
            "is_useful": safe_bool(row.get("is_useful_comment")),
            "sentiment_score": sentiment,
            "place_category": safe_str(row.get("place_category")),
            "content_latitude": safe_float(row.get("content_latitude")),
            "content_longitude": safe_float(row.get("content_longitude")),
            "media_latitude": safe_float(row.get("media_latitude")),
            "media_longitude": safe_float(row.get("media_longitude")),
            "photo_count": safe_int(row.get("photo_count"), 0),
            "video_count": safe_int(row.get("video_count"), 0),
            "image_count": safe_int(row.get("image_count"), 0),
            "media_count": safe_int(row.get("media_count"), 0),
            **topics,
            "risk_flags": "|".join(flags),
            "risk_flag_count": len(flags),
            "has_risk_flag": bool(flags),
            "scraped_at": normalize_datetime(row.get("scraped_at")),
        })

        feature_rows.append({
            "source_record_id": source_id,
            "place_id": safe_str(row.get("place_id")),
            "platform": "tiktok",
            "query": safe_str(row.get("query")),
            "video_url": safe_str(row.get("video_url")),
            "video_caption": clean_text(row.get("video_caption")),
            "video_views": safe_int(row.get("video_views"), 0),
            "video_likes": safe_int(row.get("video_likes"), 0),
            "video_comment_count": safe_int(row.get("video_comment_count"), 0),
            "comment_id": safe_str(row.get("comment_id")),
            "comment_author": safe_str(row.get("comment_author")),
            "comment_likes": safe_int(row.get("comment_likes"), 0),
            "comment_is_likely_spam": safe_bool(row.get("comment_is_likely_spam")),
            "comment_is_reply": safe_bool(row.get("comment_is_reply")),
            "comment_emoji_ratio": explicit_ratio,
        })

    return pd.DataFrame(common_rows), pd.DataFrame(feature_rows)


def normalize_facebook(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    common_rows: List[Dict[str, Any]] = []
    feature_rows: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        source_id = safe_str(row.get("id")) or safe_str(row.get("comment_id"))
        text = clean_text(row.get("comment_text"))
        quality = safe_float(row.get("comment_quality_score"), 0.0)
        sentiment = compute_sentiment(text)
        topics = compute_topic_scores(text)
        reject_reason = safe_str(row.get("comment_reject_reason"))
        flags = build_risk_flags(
            text,
            quality,
            "facebook",
            reject_reason=reject_reason,
        )

        common_rows.append({
            "normalized_id": make_id("facebook", source_id),
            "place_id": safe_str(row.get("place_id")),
            "place_name": safe_str(row.get("place_name")),
            "platform": "facebook",
            "source_record_id": source_id,
            "content_text": text,
            "rating": 0.0,
            "content_created_at": normalize_datetime(row.get("comment_created_at")),
            "author_id_or_name": safe_str(row.get("comment_author")) or safe_str(row.get("comment_author_url")),
            "engagement_count": safe_int(row.get("comment_likes"), 0),
            "language": safe_str(row.get("comment_language")),
            "quality_score": quality,
            "is_useful": safe_bool(row.get("is_useful_comment")),
            "sentiment_score": sentiment,
            "place_category": safe_str(row.get("place_category")),
            "content_latitude": safe_float(row.get("content_latitude")),
            "content_longitude": safe_float(row.get("content_longitude")),
            "media_latitude": safe_float(row.get("media_latitude")),
            "media_longitude": safe_float(row.get("media_longitude")),
            "photo_count": safe_int(row.get("photo_count"), 0),
            "video_count": safe_int(row.get("video_count"), 0),
            "image_count": safe_int(row.get("image_count"), 0),
            "media_count": safe_int(row.get("media_count"), 0),
            **topics,
            "risk_flags": "|".join(flags),
            "risk_flag_count": len(flags),
            "has_risk_flag": bool(flags),
            "scraped_at": normalize_datetime(row.get("scraped_at")),
        })

        feature_rows.append({
            "source_record_id": source_id,
            "place_id": safe_str(row.get("place_id")),
            "platform": "facebook",
            "target_origin": safe_str(row.get("target_origin")),
            "source_url": safe_str(row.get("source_url")),
            "post_url": safe_str(row.get("post_url")),
            "post_id": safe_str(row.get("post_id")),
            "post_text": clean_text(row.get("post_text")),
            "post_author": safe_str(row.get("post_author")),
            "post_comments_count": safe_int(row.get("post_comments_count"), 0),
            "post_relevance_score": safe_float(row.get("post_relevance_score"), 0.0),
            "comment_id": safe_str(row.get("comment_id")),
            "comment_author": safe_str(row.get("comment_author")),
            "comment_author_url": safe_str(row.get("comment_author_url")),
            "comment_likes": safe_int(row.get("comment_likes"), 0),
            "comment_depth": safe_int(row.get("comment_depth"), 0),
            "comment_reject_reason": reject_reason,
        })

    return pd.DataFrame(common_rows), pd.DataFrame(feature_rows)


def add_normalized_engagement(common: pd.DataFrame) -> pd.DataFrame:
    out = common.copy()
    out["engagement_count"] = pd.to_numeric(out["engagement_count"], errors="coerce").fillna(0)
    out["normalized_engagement"] = (
        out.groupby("platform")["engagement_count"].rank(method="average", pct=True).fillna(0)
    )
    out["normalized_engagement"] = out["normalized_engagement"].round(4)
    return out[COMMON_COLUMNS]


def aggregate_platform_summary(
    common: pd.DataFrame,
    google_features: pd.DataFrame,
    master: pd.DataFrame,
) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    master_lookup = master.set_index("place_id").to_dict(orient="index")

    for (place_id, platform), group in common.groupby(["place_id", "platform"], dropna=False):
        group = group.copy()
        record_count = len(group)
        useful_count = int(group["is_useful"].astype(bool).sum())
        risk_count = int(group["has_risk_flag"].astype(bool).sum())
        sentiment = pd.to_numeric(group["sentiment_score"], errors="coerce").fillna(0)
        quality = pd.to_numeric(group["quality_score"], errors="coerce").fillna(0)
        engagement = pd.to_numeric(group["normalized_engagement"], errors="coerce").fillna(0)

        row: Dict[str, Any] = {
            "place_id": place_id,
            "place_name": safe_str(group["place_name"].iloc[0]) or safe_str(master_lookup.get(place_id, {}).get("title")),
            "platform": platform,
            "record_count": record_count,
            "useful_record_count": useful_count,
            "avg_sentiment_score": round(float(sentiment.mean()), 4),
            "negative_sentiment_ratio": round(float((sentiment < -0.1).mean()), 4),
            "avg_quality_score": round(float(quality.mean()), 4),
            "useful_record_ratio": round(useful_count / max(record_count, 1), 4),
            "risk_flag_record_ratio": round(risk_count / max(record_count, 1), 4),
            "avg_normalized_engagement": round(float(engagement.mean()), 4),
        }

        for topic in TOPIC_COLUMNS:
            topic_values = pd.to_numeric(group[topic], errors="coerce").fillna(0)
            row[f"avg_{topic}"] = round(float(topic_values.mean()), 4)

        if platform == "google_maps":
            gf = google_features[google_features["place_id"] == place_id].copy()
            ratings = pd.to_numeric(gf["rating"], errors="coerce").dropna()
            row["google_maps_rating_avg_from_reviews"] = round(float(ratings.mean()), 4) if len(ratings) else 0.0
            row["google_maps_rating_master"] = safe_float(master_lookup.get(place_id, {}).get("total_score"), 0.0)
            for rating in range(1, 6):
                row[f"google_maps_rating_{rating}_count"] = int((ratings.round().astype(int) == rating).sum()) if len(ratings) else 0
        else:
            row["google_maps_rating_avg_from_reviews"] = ""
            row["google_maps_rating_master"] = ""
            for rating in range(1, 6):
                row[f"google_maps_rating_{rating}_count"] = ""

        rows.append(row)

    return pd.DataFrame(rows).sort_values(["place_id", "platform"]).reset_index(drop=True)


def compute_topic_gap(platform_rows: pd.DataFrame) -> float:
    gaps = []
    for topic in TOPIC_COLUMNS:
        column = f"avg_{topic}"
        values = pd.to_numeric(platform_rows[column], errors="coerce").fillna(0)
        if len(values) > 0:
            gaps.append(float(values.max() - values.min()))
    return round(max(gaps) if gaps else 0.0, 4)


def score_risk_for_place(
    place_id: str,
    platform_rows: pd.DataFrame,
    master_row: Dict[str, Any],
) -> Dict[str, Any]:
    sentiment_values = pd.to_numeric(platform_rows["avg_sentiment_score"], errors="coerce").fillna(0)
    sentiment_gap = round(float(sentiment_values.max() - sentiment_values.min()), 4)
    topic_gap = compute_topic_gap(platform_rows)

    maps_row = platform_rows[platform_rows["platform"] == "google_maps"]
    social_rows = platform_rows[platform_rows["platform"].isin(["tiktok", "facebook"])]

    maps_rating = safe_float(master_row.get("total_score"), 0.0)
    maps_sentiment = float(maps_row["avg_sentiment_score"].iloc[0]) if len(maps_row) else 0.0
    social_sentiment = (
        float(pd.to_numeric(social_rows["avg_sentiment_score"], errors="coerce").fillna(0).mean())
        if len(social_rows)
        else 0.0
    )

    maps_rating_positive = (maps_rating - 3.0) / 2.0 if maps_rating > 0 else maps_sentiment
    negative_social_vs_maps_gap = round(
        clamp(maps_rating_positive - social_sentiment, 0.0, 2.0) / 2.0,
        4,
    )

    useful_ratios = pd.to_numeric(platform_rows["useful_record_ratio"], errors="coerce").fillna(0)
    avg_useful_ratio = float(useful_ratios.mean()) if len(useful_ratios) else 0.0
    coverage_risk = round(clamp(1.0 - avg_useful_ratio), 4)

    risk_ratios = pd.to_numeric(platform_rows["risk_flag_record_ratio"], errors="coerce").fillna(0)
    data_quality_risk = round(float(risk_ratios.mean()) if len(risk_ratios) else 0.0, 4)

    engagement_values = pd.to_numeric(platform_rows["avg_normalized_engagement"], errors="coerce").fillna(0)
    engagement_gap = round(float(engagement_values.max() - engagement_values.min()), 4)

    risk_score = (
        data_quality_risk * 0.30
        + sentiment_gap * 0.20
        + topic_gap * 0.15
        + negative_social_vs_maps_gap * 0.20
        + coverage_risk * 0.10
        + engagement_gap * 0.05
    )
    risk_score = round(clamp(risk_score), 4)

    if risk_score < 0.33:
        risk_level = "low"
    elif risk_score < 0.66:
        risk_level = "medium"
    else:
        risk_level = "high"

    return {
        "place_id": place_id,
        "place_name": safe_str(master_row.get("title")) or safe_str(platform_rows["place_name"].iloc[0]),
        "google_maps_rating": maps_rating,
        "google_maps_rating_avg_from_reviews": (
            safe_float(maps_row["google_maps_rating_avg_from_reviews"].iloc[0], 0.0)
            if len(maps_row)
            else 0.0
        ),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "data_quality_risk": data_quality_risk,
        "sentiment_gap": sentiment_gap,
        "negative_social_vs_maps_gap": negative_social_vs_maps_gap,
        "topic_gap": topic_gap,
        "engagement_gap": engagement_gap,
        "coverage_risk": coverage_risk,
        "google_maps_avg_sentiment": maps_sentiment,
        "social_avg_sentiment": round(social_sentiment, 4),
    }


def build_place_risk(summary: pd.DataFrame, master: pd.DataFrame, complete_place_ids: Sequence[str]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    master_lookup = master.set_index("place_id").to_dict(orient="index")

    for place_id in complete_place_ids:
        platform_rows = summary[summary["place_id"] == place_id]
        found_platforms = set(platform_rows["platform"])
        if not set(REQUIRED_PLATFORMS).issubset(found_platforms):
            continue
        rows.append(score_risk_for_place(place_id, platform_rows, master_lookup.get(place_id, {})))

    return pd.DataFrame(rows).sort_values("place_id").reset_index(drop=True)


def compute_place_weighted_rating(common: pd.DataFrame) -> pd.DataFrame:
    """Weighted average rating using final_trust_score as weight — Google Maps only."""
    gm = common[
        (common["platform"] == "google_maps")
        & (pd.to_numeric(common["rating"], errors="coerce") > 0)
    ].copy()
    gm["rating_num"] = pd.to_numeric(gm["rating"], errors="coerce")
    gm["trust_weight"] = pd.to_numeric(gm["final_trust_score"], errors="coerce").fillna(0).clip(lower=0)

    rows: List[Dict[str, Any]] = []
    for place_id, group in gm.groupby("place_id"):
        total_weight = float(group["trust_weight"].sum())
        if total_weight > 0:
            weighted_rating = float((group["rating_num"] * group["trust_weight"]).sum() / total_weight)
        else:
            weighted_rating = float(group["rating_num"].mean())

        all_place = common[common["place_id"] == place_id]
        rows.append({
            "place_id": place_id,
            "place_name": safe_str(group["place_name"].iloc[0]),
            "google_review_count": len(group),
            "raw_avg_rating": round(float(group["rating_num"].mean()), 4),
            "weighted_avg_rating": round(weighted_rating, 4),
            "avg_trust_score_google": round(float(group["trust_weight"].mean()), 4),
            "high_trust_count": int((group["trust_weight"] >= 0.65).sum()),
            "medium_trust_count": int(((group["trust_weight"] >= 0.35) & (group["trust_weight"] < 0.65)).sum()),
            "low_trust_count": int((group["trust_weight"] < 0.35).sum()),
            "outlier_count_all_platforms": int((all_place["review_flag"] == "outlier").sum()),
        })
    return pd.DataFrame(rows).sort_values("place_id").reset_index(drop=True)


def flag_contains(row: pd.Series, needle: str) -> bool:
    values = [
        safe_str(row.get("risk_flags")),
        safe_str(row.get("trust_flags_layer1")),
        safe_str(row.get("trust_flags_layer2")),
        safe_str(row.get("trust_flags_layer3")),
    ]
    return any(needle in value for value in values if value)


def is_trusted_level(row: pd.Series) -> bool:
    return safe_str(row.get("trust_level")).lower() in {"medium", "high"}


def is_supported_language(row: pd.Series) -> bool:
    language = safe_str(row.get("language")).lower()
    # Google Maps often has blank language in the current crawl output.
    return language in {"", "vi", "en"}


def is_not_spam_or_seed(row: pd.Series) -> bool:
    if safe_bool(row.get("nlp_seeding_detected")):
        return False
    blocked_flags = [
        "seeding_or_promo_language",
        "seeding_language",
        "likely_spam",
        "empty_text",
        "rating_without_text",
    ]
    return not any(flag_contains(row, flag) for flag in blocked_flags)


def build_filtered_outputs(common: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    out = common.copy()
    out["rating"] = pd.to_numeric(out["rating"], errors="coerce").fillna(0)

    trusted = out.apply(is_trusted_level, axis=1)
    supported_language = out.apply(is_supported_language, axis=1)
    not_spam_or_seed = out.apply(is_not_spam_or_seed, axis=1)
    useful = out["is_useful"].astype(bool)
    google = out["platform"] == "google_maps"
    social = out["platform"].isin(["tiktok", "facebook"])

    google_clean = out[
        google
        & trusted
        & supported_language
        & not_spam_or_seed
        & useful
        & (out["rating"] > 0)
        & ~out.apply(lambda row: flag_contains(row, "too_short_text"), axis=1)
    ].copy()

    social_review_clean = out[
        social
        & trusted
        & supported_language
        & not_spam_or_seed
        & useful
    ].copy()

    # Keep short social comments here because they can still represent engagement,
    # but remove clear spam/seeding/empty records.
    social_engagement_clean = out[
        social
        & supported_language
        & not_spam_or_seed
    ].copy()

    all_clean = pd.concat([google_clean, social_review_clean], ignore_index=True)

    summary_rows: List[Dict[str, Any]] = []
    for name, frame in [
        ("raw_all", out),
        ("clean_all_trusted_records", all_clean),
        ("clean_google_maps_reviews", google_clean),
        ("clean_social_review_signals", social_review_clean),
        ("clean_social_engagement_signals", social_engagement_clean),
    ]:
        ratings = pd.to_numeric(frame.get("rating", pd.Series(dtype=float)), errors="coerce")
        valid_ratings = ratings[ratings > 0]
        summary_rows.append({
            "dataset": name,
            "record_count": len(frame),
            "google_maps_count": int((frame["platform"] == "google_maps").sum()) if "platform" in frame else 0,
            "tiktok_count": int((frame["platform"] == "tiktok").sum()) if "platform" in frame else 0,
            "facebook_count": int((frame["platform"] == "facebook").sum()) if "platform" in frame else 0,
            "avg_final_trust_score": round(float(pd.to_numeric(frame.get("final_trust_score", pd.Series(dtype=float)), errors="coerce").mean()), 4) if len(frame) else 0.0,
            "avg_rating": round(float(valid_ratings.mean()), 4) if len(valid_ratings) else 0.0,
            "total_engagement": int(pd.to_numeric(frame.get("engagement_count", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if len(frame) else 0,
        })

    return {
        "clean_trusted_records": all_clean,
        "clean_google_maps_reviews": google_clean,
        "clean_social_review_signals": social_review_clean,
        "clean_social_engagement_signals": social_engagement_clean,
        "filtering_quality_summary": pd.DataFrame(summary_rows),
    }


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def build_cross_platform_dataset(args: argparse.Namespace) -> Dict[str, Path]:
    master = read_csv(args.master_file)
    google_raw = read_csv(args.google_maps_file)
    tiktok_raw = read_csv(args.tiktok_file)
    facebook_raw = read_csv(args.facebook_file)

    frames = {
        "google_maps": google_raw,
        "tiktok": tiktok_raw,
        "facebook": facebook_raw,
    }
    complete_place_ids = get_complete_place_ids(frames, master)
    if not complete_place_ids:
        raise ValueError("No place_id has all required platforms.")

    google = prepare_frame(google_raw, complete_place_ids)
    tiktok = prepare_frame(tiktok_raw, complete_place_ids)
    facebook = prepare_frame(facebook_raw, complete_place_ids)
    master = master[master["place_id"].isin(complete_place_ids)].copy()

    google_common, google_features = normalize_google_maps(google, master)
    tiktok_common, tiktok_features = normalize_tiktok(tiktok)
    facebook_common, facebook_features = normalize_facebook(facebook)

    common = pd.concat(
        [google_common, tiktok_common, facebook_common],
        ignore_index=True,
    )
    common = add_normalized_engagement(common)

    common = compute_layer1_behavior_scores(common, master)
    common = add_translation_normalization(common, args.output_dir / TRANSLATION_CACHE_FILE.name)
    common = compute_layer2_nlp_scores(common)

    common["intermediate_trust_score"] = (
        0.50
        + pd.to_numeric(common["trust_score_layer1"], errors="coerce").fillna(0)
        + pd.to_numeric(common["trust_score_layer2"], errors="coerce").fillna(0)
    ).clip(0.0, 1.0).round(4)

    common = compute_layer3_crosscheck_scores(common)

    # final_trust_score = layer1 + layer2 only (independent review quality)
    common["final_trust_score"] = common["intermediate_trust_score"]

    # consistency_score = layer3 signal (how consistent vs place baseline)
    common["consistency_score"] = pd.to_numeric(
        common["trust_score_layer3"], errors="coerce"
    ).fillna(0.0).round(4)

    # review_flag: outlier when consistency is significantly low
    common["review_flag"] = common["consistency_score"].apply(
        lambda s: "outlier" if s < -0.20 else "normal"
    )

    common["trust_level"] = common["final_trust_score"].apply(
        lambda s: "high" if s >= 0.65 else ("low" if s < 0.35 else "medium")
    )

    summary = aggregate_platform_summary(common, google_features, master)
    trust_summary = aggregate_place_trust_summary(common)
    risk = build_place_risk(summary, master, complete_place_ids)
    weighted_rating = compute_place_weighted_rating(common)
    filtered_outputs = build_filtered_outputs(common)

    outputs = {
        "normalized_common_records": args.output_dir / COMMON_OUTPUT_FILE.name,
        "platform_google_maps_features": args.output_dir / GOOGLE_FEATURES_FILE.name,
        "platform_tiktok_features": args.output_dir / TIKTOK_FEATURES_FILE.name,
        "platform_facebook_features": args.output_dir / FACEBOOK_FEATURES_FILE.name,
        "place_platform_summary": args.output_dir / SUMMARY_OUTPUT_FILE.name,
        "place_cross_platform_risk": args.output_dir / RISK_OUTPUT_FILE.name,
        "place_review_trust_summary": args.output_dir / TRUST_OUTPUT_FILE.name,
        "place_weighted_rating": args.output_dir / WEIGHTED_RATING_FILE.name,
        "clean_trusted_records": args.output_dir / CLEAN_ALL_FILE.name,
        "clean_google_maps_reviews": args.output_dir / CLEAN_GOOGLE_MAPS_FILE.name,
        "clean_social_review_signals": args.output_dir / CLEAN_SOCIAL_REVIEWS_FILE.name,
        "clean_social_engagement_signals": args.output_dir / CLEAN_SOCIAL_ENGAGEMENT_FILE.name,
        "filtering_quality_summary": args.output_dir / FILTERING_SUMMARY_FILE.name,
    }

    write_csv(common, outputs["normalized_common_records"])
    write_csv(google_features, outputs["platform_google_maps_features"])
    write_csv(tiktok_features, outputs["platform_tiktok_features"])
    write_csv(facebook_features, outputs["platform_facebook_features"])
    write_csv(summary, outputs["place_platform_summary"])
    write_csv(risk, outputs["place_cross_platform_risk"])
    write_csv(trust_summary, outputs["place_review_trust_summary"])
    write_csv(weighted_rating, outputs["place_weighted_rating"])
    write_csv(filtered_outputs["clean_trusted_records"], outputs["clean_trusted_records"])
    write_csv(filtered_outputs["clean_google_maps_reviews"], outputs["clean_google_maps_reviews"])
    write_csv(filtered_outputs["clean_social_review_signals"], outputs["clean_social_review_signals"])
    write_csv(filtered_outputs["clean_social_engagement_signals"], outputs["clean_social_engagement_signals"])
    write_csv(filtered_outputs["filtering_quality_summary"], outputs["filtering_quality_summary"])

    print("Cross-platform dataset built.")
    print(f"Complete places: {', '.join(complete_place_ids)}")
    print(f"Normalized records: {len(common)}")
    print(f"Place-platform summary rows: {len(summary)}")
    print(f"Risk rows: {len(risk)}")
    for name, path in outputs.items():
        print(f"{name}: {path}")

    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build normalized cross-platform datasets and place risk scores."
    )
    parser.add_argument("--master-file", type=Path, default=MASTER_PLACES_FILE)
    parser.add_argument("--google-maps-file", type=Path, default=GOOGLE_MAPS_FILE)
    parser.add_argument("--tiktok-file", type=Path, default=TIKTOK_FILE)
    parser.add_argument("--facebook-file", type=Path, default=FACEBOOK_FILE)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    build_cross_platform_dataset(parse_args())


if __name__ == "__main__":
    main()
