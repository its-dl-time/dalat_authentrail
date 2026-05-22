import os
import re
import time
import hashlib
import json
import argparse
import sys
from datetime import datetime
from collections import defaultdict
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from apify_client import ApifyClient

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from urllib.request import urlopen, Request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# =====================
# CONFIG
# =====================

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
if not APIFY_TOKEN:
    raise ValueError("Missing APIFY_TOKEN in .env")

ACTOR_ID = "clockworks/tiktok-scraper"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
TIKTOK_OUTPUT_DIR = DATA_DIR / "outputs" / "tiktok"
TIKTOK_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TIKTOK_RAW_VIDEO_DIR = DATA_DIR / "raw" / "tiktok" / "videos"
TIKTOK_RAW_COMMENT_DIR = DATA_DIR / "raw" / "tiktok" / "comments"
TIKTOK_INTERIM_DIR = DATA_DIR / "interim"
TIKTOK_RAW_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
TIKTOK_RAW_COMMENT_DIR.mkdir(parents=True, exist_ok=True)
TIKTOK_INTERIM_DIR.mkdir(parents=True, exist_ok=True)

PLACES_FILE = PROCESSED_DATA_DIR / "places_master_top50.csv"

VIDEO_SEEDS_FILE = TIKTOK_OUTPUT_DIR / "tiktok_video_seeds.csv"
COMMENTS_OUTPUT_FILE = TIKTOK_OUTPUT_DIR / "tiktok_comments_output.csv"
VIDEO_REJECTIONS_FILE = TIKTOK_OUTPUT_DIR / "tiktok_video_rejections.csv"
COMMENT_REJECTIONS_FILE = TIKTOK_OUTPUT_DIR / "tiktok_comment_rejections.csv"
VIDEO_CANDIDATES_FILE = TIKTOK_INTERIM_DIR / "tiktok_video_candidates.csv"
COMMENT_CANDIDATES_FILE = TIKTOK_INTERIM_DIR / "tiktok_comment_candidates.csv"

MAX_PLACES = 5
QUERIES_PER_PLACE = 2
DISCOVERY_VIDEOS_PER_QUERY = 20
MAX_SEED_VIDEOS_PER_QUERY = 10
MAX_SEED_VIDEOS_TOTAL_PER_PLACE = 20  # Cap total seed videos per place
COMMENTS_PER_VIDEO = 50

MIN_VIDEO_COMMENTS = 10
MIN_RELEVANCE_SCORE = 3.5  # Raised from 3.5 for stricter filtering
MAX_REPLIES_PER_COMMENT = 1

SLEEP_SECONDS = 1  # Reduced from 3 (no rate limiting by Apify)
BATCH_COMMENT_URLS = 5  # Batch 5 video URLs per comment crawl (optimization)

# Comment quality thresholds
MIN_COMMENT_WORDS = 10  # Raised from 4 (better for NLP)
MIN_USEFUL_TERMS_MATCH = 2  # Require 2+ useful term matches (stricter)
MAX_EMOJI_RATIO = 0.3  # Flag comments with >30% emojis as LOW_TEXT_QUALITY

# Telemetry tracking
STATS = {
    "videos_searched": 0,
    "videos_too_few_comments": 0,
    "videos_low_relevance": 0,
    "videos_selected": 0,
    "api_calls": 0,
    "comments_total": 0,
    "comments_by_filter": defaultdict(int),
}

client = ApifyClient(APIFY_TOKEN)


# =====================
# HELPERS
# =====================

def clean_text(text):
    if text is None:
        return ""
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_text(text):
    text = clean_text(text).lower()
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"[^\w\sÀ-ỹ]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def make_id(*parts):
    raw = "|".join([str(p) for p in parts if p is not None])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def canonical_url(url):
    url = clean_text(url)
    if not url:
        return ""
    return url.split("?")[0].rstrip("/")


def safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def read_existing_csv(file_path):
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return pd.DataFrame()

    try:
        return pd.read_csv(file_path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def save_csv(df, file_path, append=False, dedupe_subset=None):
    if append:
        existing_df = read_existing_csv(file_path)
        if len(existing_df) > 0:
            df = pd.concat([existing_df, df], ignore_index=True)

    if len(df) > 0 and dedupe_subset:
        available_subset = [column for column in dedupe_subset if column in df.columns]
        if available_subset:
            df = df.drop_duplicates(subset=available_subset, keep="last")

    df.to_csv(file_path, index=False, encoding="utf-8-sig")
    return df


def select_places_slice(places, start_row=1, end_row=None, limit=None):
    """
    Select places from master CSV by 1-based data rows.
    Row 1 means the first data row after the CSV header.
    """
    total_rows = len(places)

    if total_rows == 0:
        return places

    if start_row < 1:
        raise ValueError("--start-row must be >= 1")

    if end_row is not None and end_row < start_row:
        raise ValueError("--end-row must be >= --start-row")

    if limit is not None and limit < 1:
        raise ValueError("--limit must be >= 1")

    start_index = start_row - 1

    if start_index >= total_rows:
        raise ValueError(
            f"--start-row={start_row} is outside the master CSV range "
            f"(1-{total_rows})"
        )

    if end_row is not None:
        end_index = min(end_row, total_rows)
    elif limit is not None:
        end_index = min(start_index + limit, total_rows)
    else:
        end_index = min(start_index + MAX_PLACES, total_rows)

    return places.iloc[start_index:end_index].copy()


def get_author_username(comment):
    author = comment.get("author") or comment.get("user") or {}

    if isinstance(author, dict):
        return (
            author.get("uniqueId")
            or author.get("nickname")
            or author.get("username")
            or author.get("name")
            or ""
        )

    return str(author)


def get_comment_text(comment):
    for key in [
        "text",
        "comment",
        "content",
        "replyComment",
        "shareText"
    ]:
        value = clean_text(comment.get(key))
        if value:
            return value

    return ""


# =====================
# PHASE 1: IMPROVED FILTERS & QUALITY DETECTION
# =====================

def count_emojis(text):
    """Count approximate emojis in text."""
    if not text:
        return 0
    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001F9FF"  # Emoticons & pictographs
        "\U0001F600-\U0001F64F"  # Emoticons
        "\u2600-\u27BF"          # Miscellaneous Symbols
        "\U0001f900-\U0001f9ff"  # Supplemental Symbols & Pictographs
        "]+", flags=re.UNICODE
    )
    return len(emoji_pattern.findall(text))


def emoji_ratio(text):
    """Calculate emoji ratio in text (emoji_count / total_characters)."""
    if not text:
        return 0
    emoji_count = count_emojis(text)
    if emoji_count == 0:
        return 0
    return emoji_count / len(text)


def detect_comment_language(text):
    """
    Detect if text is primarily Vietnamese.
    Returns: "vi", "en", "other", or "mixed"
    """
    if not text:
        return "unknown"
    
    # Vietnamese character ranges: À-ỹ
    vietnamese_chars = sum(1 for c in text if ord(c) >= 192 and ord(c) <= 7871)
    # English (A-Z, a-z)
    english_chars = sum(1 for c in text if c.isalpha() and ord(c) < 128)
    total_alpha = vietnamese_chars + english_chars
    
    if total_alpha == 0:
        return "unknown"
    
    if vietnamese_chars / total_alpha > 0.6:
        return "vi"
    elif english_chars / total_alpha > 0.6:
        return "en"
    elif vietnamese_chars > 0 and english_chars > 0:
        return "mixed"
    else:
        return "other"


def is_likely_spam(comment_text, author_username=""):
    """
    Detect likely spam/bot comments.
    Returns: True if likely spam, False if probably legitimate.
    """
    t = normalize_text(comment_text)
    
    if not t:
        return True
    
    # Extremely short messages (suspicious)
    if len(t) < 2:
        return True
    
    # Emoji-only or emoji-heavy
    if len(comment_text.strip()) < 3 and emoji_ratio(comment_text) > 0.5:
        return True
    
    # Repeated characters (spam pattern)
    if re.search(r"([a-zàáảãạăằắẳẵặâầấẩẫậ])\1{4,}", t):
        return True
    
    # Spam hashtags/links (obfuscated)
    if t.count("#") > 3 or t.count("http") > 1:
        return True
    
    # All caps (often spam)
    if len(t.split()) >= 3 and t.isupper():
        return True
    
    return False


def comment_quality_score(comment_text):
    """
    Compute comment quality score (0-1).
    Factors: text length, emoji ratio, language, spam likelihood.
    Returns: float 0-1, where 1 is highest quality.
    """
    if not comment_text:
        return 0.0
    
    t = comment_text.strip()
    score = 0.0
    
    # Length factor (ideal: 40-500 chars)
    text_len = len(t)
    if 40 <= text_len <= 500:
        score += 0.4
    elif 20 <= text_len < 40:
        score += 0.2
    elif text_len > 500:
        score += 0.3
    
    # Emoji ratio factor (good: <10%)
    emoji_rat = emoji_ratio(t)
    if emoji_rat < 0.1:
        score += 0.3
    elif emoji_rat < 0.3:
        score += 0.15
    else:
        score += 0.0
    
    # Language detection (prefer Vietnamese)
    lang = detect_comment_language(t)
    if lang == "vi":
        score += 0.2
    elif lang == "mixed":
        score += 0.1
    
    # Spam likelihood (penalize)
    if is_likely_spam(t):
        score = max(0, score - 0.3)
    
    return min(1.0, round(score, 2))


def is_reply_greeting(comment_text):
    """
    Detect if comment is a greeting/thank-you reply (typically from owner).
    Returns: True if it's a greeting pattern, False otherwise.
    """
    if not comment_text:
        return False
    
    t = normalize_text(comment_text)
    
    # Owner/shop greeting patterns
    greeting_patterns = [
        "dạ cảm ơn", "da cam on",
        "cảm ơn bạn", "cam on ban",
        "xin cảm ơn", "xin cam on",
        "cảm ơn ạ", "cam on a",
        "vâng cảm ơn", "vang cam on",
        "dạ vâng", "da vang",
        "dạ chị", "da chi",
        "dạ bạn", "da ban",
        "thank you", "thanks",
        "cảm ơn", "cam on",  # Generic thank you
        "vâng ạ", "vang a",
        "xin chào", "xin chao",
    ]
    
    # If comment is very short + has greeting pattern → likely a reply
    if len(t.split()) <= 5:
        if any(pattern in t for pattern in greeting_patterns):
            return True
    
    # If comment starts with greeting pattern
    if any(t.startswith(pattern) for pattern in greeting_patterns):
        return True
    
    return False


def is_reply_from_owner(comment_author, video_author):
    """
    Detect if comment is from the video owner (shop owner replying).
    Compares author usernames.
    Returns: True if likely same person, False otherwise.
    """
    if not comment_author or not video_author:
        return False
    
    comment_author = str(comment_author).strip().lower()
    video_author = str(video_author).strip().lower()
    
    if not comment_author or not video_author:
        return False
    
    # Exact match or contains relationship
    if comment_author == video_author:
        return True
    
    # Handle account name variations (e.g., "quanngondalat" could be owner of videos about their shop)
    # Simple heuristic: if one contains the other significantly
    if len(comment_author) > 0 and len(video_author) > 0:
        if comment_author in video_author or video_author in comment_author:
            return True
    
    return False


def is_useful_comment(text, place_name):
    """
    Enhanced version: higher word count, multiple useful terms required.
    Still returns True/False for backward compatibility.
    """
    t = normalize_text(text)

    if not t:
        return False

    # Raised minimum from 4 to 10 words
    if len(t.split()) < MIN_COMMENT_WORDS:
        return False

    # Expanded junk terms (~50 patterns)
    junk_terms = [
        "xin địa chỉ", "xin dia chi", "ở đâu", "o dau",
        "ib", "inbox", "xin giá", "xin gia",
        "tag", "chấm", "hóng", "rep em",
        "xin thêm info", "xin thong tin", "lien he",
        "gọi", "call", "zalo", "shopee", "fb",
        "bao nhiêu tiền", "gia bao nhieu", "giá",
        "mấy giờ mở", "mo cua luc nao", "gio lam viec",
        "đặt bàn", "dat ban", "reserv",
        "ship", "giao hang", "delivery",
        "code", "coupon", "voucher", "discount",
        "hộp thư", "pm", "dm", "message",
        "follow", "like", "subscribe", "channel"
    ]

    if any(term in t for term in junk_terms):
        return False

    # Expanded useful terms (~40 patterns)
    useful_terms = [
        "mình đi", "tui đi", "đã đi", "vừa đi", "lần trước",
        "trải nghiệm", "trai nghiem", "kinh nghiệm", "review",
        "giá", "đắt", "rẻ", "mắc", "re", "dat",
        "đông", "vắng", "dong", "vang",
        "đẹp", "xấu", "dep", "xau",
        "ngon", "dở", "ngon", "do", "chua",
        "phục vụ", "phuc vu", "dich vu", "service",
        "thái độ", "thai do", "attitude",
        "đáng đi", "không đáng", "dang di", "ko dang",
        "thất vọng", "that vong", "hanh phuc",
        "quay lại", "không quay lại", "repeat",
        "ngoài đời", "khác ảnh", "ngoai doi", "khac anh",
        "lừa", "chặt chém", "lua", "chat chem",
        "vé", "gửi xe", "ve", "gui xe",
        "không gian", "khong gian", "space",
        "sạch sẽ", "sach se", "clean",
        "tươi", "mới", "tuoi", "moi",
        "cách", "cach", "way",
        "lạc", "lac", "lost", "found"
    ]

    # Require 2+ useful terms (stricter than before)
    matched_terms = sum(1 for term in useful_terms if term in t)
    if matched_terms >= MIN_USEFUL_TERMS_MATCH:
        return True

    # Fallback: place name match
    place_norm = normalize_text(place_name)
    if place_norm and place_norm in t and matched_terms >= 1:
        return True

    return False


# =====================
# QUERY
# =====================

def build_queries(place_name, category=""):
    queries = [
        f"{place_name} Đà Lạt review",
        f"{place_name} Đà Lạt",
        f"review {place_name}",
    ]

    category_lower = str(category).lower()

    if any(x in category_lower for x in ["cà phê", "cafe", "quán ăn", "nhà hàng", "restaurant"]):
        queries.append(f"{place_name} ngon không")

    if any(x in category_lower for x in ["du lịch", "tourist", "attraction", "điểm du lịch"]):
        queries.append(f"{place_name} có đáng đi không")

    return queries[:QUERIES_PER_PLACE]


# =====================
# FILTERS
# =====================

def video_relevance_score(video, place_name, query):
    """
    Enhanced scoring: stricter thresholds, improved weighting for NLP quality.
    """
    caption = normalize_text(video.get("text", ""))
    place = normalize_text(place_name)
    query_norm = normalize_text(query)

    comments = safe_int(video.get("commentCount", 0))
    views = safe_int(video.get("playCount", 0))
    likes = safe_int(video.get("diggCount", 0))

    score = 0
    
    # Caption length penalty (very short captions are low quality)
    caption_len = len(video.get("text", ""))
    if caption_len < 20:
        score -= 1
    elif caption_len > 200:
        score += 0.5

    # Place name relevance (most important)
    if place and place in caption:
        score += 4

    # Location context (important for regional analysis)
    if "đà lạt" in caption or "dalat" in caption or "da lat" in caption:
        score += 2  # Increased from 1

    # Query token matching (improved weighting)
    query_tokens = [t for t in query_norm.split() if len(t) >= 3]
    if query_tokens:
        matched = sum(1 for t in query_tokens if t in caption)
        query_match_ratio = matched / len(query_tokens)
        # If both place and query match, boost score
        if place and place in caption:
            score += min(3, query_match_ratio * 3)  # Increased from max 2
        else:
            score += min(2, query_match_ratio * 2)

    # Engagement metrics (secondary)
    if comments >= 100:
        score += 1
    elif comments >= 50:
        score += 0.5

    if views >= 10000:
        score += 0.5
    elif views >= 5000:
        score += 0.25

    if likes >= 300:
        score += 0.5
    elif likes >= 150:
        score += 0.25

    return round(max(0, score), 2)


def is_useful_comment(text, place_name):
    t = normalize_text(text)

    if not t:
        return False

    if len(t.split()) < 4:
        return False

    junk_terms = [
        "xin địa chỉ", "xin dia chi", "ở đâu", "o dau",
        "ib", "inbox", "xin giá", "xin gia",
        "tag", "chấm", "hóng", "rep em"
    ]

    if any(term in t for term in junk_terms):
        return False

    useful_terms = [
        "mình đi", "tui đi", "đã đi", "vừa đi",
        "trải nghiệm", "giá", "đắt", "rẻ",
        "đông", "vắng", "đẹp", "xấu",
        "ngon", "dở", "phục vụ", "thái độ",
        "đáng đi", "không đáng", "thất vọng",
        "quay lại", "không quay lại",
        "ngoài đời", "khác ảnh", "lừa", "chặt chém",
        "vé", "gửi xe", "kẹt xe"
    ]

    if any(term in t for term in useful_terms):
        return True

    place_norm = normalize_text(place_name)
    if place_norm and place_norm in t:
        return True

    return False


# =====================
# APIFY
# =====================

def run_actor(actor_input):
    run = client.actor(ACTOR_ID).call(run_input=actor_input)
    dataset_id = run.get("defaultDatasetId")

    if not dataset_id:
        return []

    return list(client.dataset(dataset_id).iterate_items())

def extract_dataset_id_from_url(dataset_url):
    """
    Hỗ trợ URL dạng:
    https://api.apify.com/v2/datasets/DATASET_ID/items?format=json
    https://console.apify.com/storage/datasets/DATASET_ID
    """
    dataset_url = clean_text(dataset_url)
    if not dataset_url:
        return ""

    patterns = [
        r"/datasets/([^/?#]+)",
        r"datasets/([^/?#]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, dataset_url)
        if match:
            return match.group(1)

    return ""


def fetch_apify_dataset_items(dataset_url):
    """
    Lấy comments từ commentsDatasetUrl.
    Ưu tiên dùng ApifyClient nếu extract được dataset_id.
    Fallback dùng HTTP nếu cần.
    """
    dataset_url = clean_text(dataset_url)
    if not dataset_url:
        return []

    dataset_id = extract_dataset_id_from_url(dataset_url)

    if dataset_id:
        try:
            return list(client.dataset(dataset_id).iterate_items())
        except Exception as e:
            print(f"[WARN] Cannot fetch dataset by id={dataset_id}: {e}")

    try:
        parsed = urlparse(dataset_url)
        query = parse_qs(parsed.query)

        if "format" not in query:
            query["format"] = ["json"]

        if "token" not in query and APIFY_TOKEN:
            query["token"] = [APIFY_TOKEN]

        new_query = urlencode(query, doseq=True)
        final_url = urlunparse(parsed._replace(query=new_query))

        req = Request(final_url, headers={"Authorization": f"Bearer {APIFY_TOKEN}"})

        with urlopen(req, timeout=60) as response:
            data = response.read().decode("utf-8")

        import json
        parsed_data = json.loads(data)

        if isinstance(parsed_data, list):
            return parsed_data

        return []

    except Exception as e:
        print(f"[WARN] Cannot fetch commentsDatasetUrl: {e}")
        return []


def get_comments_from_video(video):
    """
    Actor có thể trả:
    1. comments trực tiếp trong video["comments"]
    2. commentsDatasetUrl riêng
    """
    comments = video.get("comments")

    if isinstance(comments, list) and len(comments) > 0:
        return comments

    comments_dataset_url = video.get("commentsDatasetUrl")

    if comments_dataset_url:
        return fetch_apify_dataset_items(comments_dataset_url)

    return []

def search_videos(query):
    actor_input = {
        "searchQueries": [query],
        "searchSection": "/video",
        "resultsPerPage": DISCOVERY_VIDEOS_PER_QUERY,
        "videoSearchSorting": "MOST_RELEVANT",
        "videoSearchDateFilter": "ALL_TIME",

        "commentsPerPost": 0,
        "topLevelCommentsPerPost": 0,
        "maxRepliesPerComment": 0,

        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
        "shouldDownloadSlideshowImages": False,
        "shouldDownloadAvatars": False,
        "shouldDownloadMusicCovers": False,
        "downloadSubtitlesOptions": "NEVER_DOWNLOAD_SUBTITLES",
    }

    return run_actor(actor_input)


def crawl_comments(video_urls):
    """
    Crawl comments from batch of video URLs.
    Optimized to batch multiple URLs per API call.
    """
    actor_input = {
        "postURLs": video_urls,
        "topLevelCommentsPerPost": COMMENTS_PER_VIDEO,  # Use only topLevelCommentsPerPost (simplified)
        "maxRepliesPerComment": MAX_REPLIES_PER_COMMENT,

        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
        "shouldDownloadSlideshowImages": False,
        "shouldDownloadAvatars": False,
        "shouldDownloadMusicCovers": False,
        "downloadSubtitlesOptions": "NEVER_DOWNLOAD_SUBTITLES",
    }

    STATS["api_calls"] += 1
    return run_actor(actor_input)


# =====================
# STAGE 1: VIDEO SEEDS
# =====================

def create_video_seeds(
    places_file=PLACES_FILE,
    start_row=1,
    end_row=None,
    limit=None,
    append_output=False,
):
    """
    Stage 1: Search for videos, filter by relevance, save seed videos.
    Now includes place metadata (category, address) for downstream NLP.
    """
    all_places = pd.read_csv(places_file)
    places = select_places_slice(
        all_places,
        start_row=start_row,
        end_row=end_row,
        limit=limit,
    )

    selected_start = places.index.min() + 1 if len(places) > 0 else 0
    selected_end = places.index.max() + 1 if len(places) > 0 else 0
    print(
        f"[INFO] Master CSV: {places_file} | "
        f"selected data rows {selected_start}-{selected_end} "
        f"({len(places)}/{len(all_places)} places)"
    )

    seed_rows = []
    rejection_log = []  # Log rejected videos for analysis

    for _, place in places.iterrows():
        place_id = clean_text(place.get("place_id", ""))
        place_name = clean_text(place.get("title", ""))
        category = clean_text(place.get("category", ""))
        address = clean_text(place.get("address", ""))
        
        queries = build_queries(place_name, category)
        place_seed_count = 0

        for query in queries:
            print(f"[SEARCH] {place_id} | {place_name} | {query}")

            try:
                videos = search_videos(query)
                STATS["api_calls"] += 1

                candidates = []

                for video in videos:
                    STATS["videos_searched"] += 1
                    
                    video_url = canonical_url(video.get("webVideoUrl", ""))
                    if not video_url:
                        continue

                    comment_count = safe_int(video.get("commentCount", 0))
                    if comment_count < MIN_VIDEO_COMMENTS:
                        STATS["videos_too_few_comments"] += 1
                        rejection_log.append({
                            "place_id": place_id,
                            "query": query,
                            "video_url": video_url,
                            "rejection_reason": f"too_few_comments_{comment_count}",
                            "relevance_score": None
                        })
                        continue

                    score = video_relevance_score(video, place_name, query)
                    if score < MIN_RELEVANCE_SCORE:
                        STATS["videos_low_relevance"] += 1
                        rejection_log.append({
                            "place_id": place_id,
                            "query": query,
                            "video_url": video_url,
                            "rejection_reason": f"low_relevance_{score}",
                            "relevance_score": score
                        })
                        continue

                    candidates.append({
                        "platform": "tiktok",
                        "place_id": place_id,
                        "place_name": place_name,
                        "place_category": category,
                        "place_address": address,
                        "query": query,
                        "video_id": video.get("id", ""),
                        "video_url": video_url,
                        "caption": clean_text(video.get("text", "")),
                        "created_at": video.get("createTimeISO", ""),
                        "author": (video.get("authorMeta") or {}).get("name", ""),
                        "views": safe_int(video.get("playCount", 0)),
                        "likes": safe_int(video.get("diggCount", 0)),
                        "shares": safe_int(video.get("shareCount", 0)),
                        "comment_count": comment_count,
                        "relevance_score": score,
                        "scraped_at": datetime.now().isoformat()
                    })

                candidates = sorted(
                    candidates,
                    key=lambda x: (x["relevance_score"], x["comment_count"], x["views"]),
                    reverse=True
                )[:MAX_SEED_VIDEOS_PER_QUERY]

                # Cap total seed videos per place
                remaining_quota = MAX_SEED_VIDEOS_TOTAL_PER_PLACE - place_seed_count
                candidates = candidates[:remaining_quota]
                
                seed_rows.extend(candidates)
                place_seed_count += len(candidates)
                STATS["videos_selected"] += len(candidates)

                if place_seed_count >= MAX_SEED_VIDEOS_TOTAL_PER_PLACE:
                    print(f"[INFO] Reached seed video quota for {place_id} ({place_seed_count})")
                    break

                time.sleep(SLEEP_SECONDS)

            except Exception as e:
                print(f"[FAILED SEARCH] {place_id} | {query} | {e}")
                continue

    seeds = pd.DataFrame(seed_rows)

    if len(seeds) > 0:
        seeds["dedupe_key"] = seeds["video_url"].apply(lambda x: f"tiktok|{canonical_url(x)}")
        seeds = seeds.sort_values(
            by=["relevance_score", "comment_count", "views"],
            ascending=[False, False, False]
        )
        seeds = seeds.drop_duplicates(subset=["dedupe_key"], keep="first")
        seeds = seeds.drop(columns=["dedupe_key"])

    current_seeds = seeds
    saved_seeds = save_csv(
        seeds,
        VIDEO_SEEDS_FILE,
        append=append_output,
        dedupe_subset=["video_url"],
    )
    
    # Log rejection reasons
    if rejection_log:
        rejection_df = pd.DataFrame(rejection_log)
        rejection_csv = VIDEO_REJECTIONS_FILE
        rejection_df = save_csv(
            rejection_df,
            rejection_csv,
            append=append_output,
            dedupe_subset=["place_id", "query", "video_url", "rejection_reason"],
        )
        print(f"[INFO] Logged {len(rejection_df)} rejected videos: {rejection_csv}")

    print(f"\n[SUMMARY] Video Seeds Stage:")
    print(f"  Total searched: {STATS['videos_searched']}")
    print(f"  Rejected (too few comments): {STATS['videos_too_few_comments']}")
    print(f"  Rejected (low relevance): {STATS['videos_low_relevance']}")
    print(f"  Selected: {STATS['videos_selected']}")
    print(f"  Saved to: {VIDEO_SEEDS_FILE}")
    print(f"  Seed videos in this run: {len(current_seeds)}")
    print(f"  Total seed videos in file: {len(saved_seeds)}")

    return current_seeds


# =====================
# STAGE 2: COMMENTS
# =====================

def create_comments_output(seeds, append_output=False):
    """
    Stage 2: Crawl comments from seed videos, apply quality filters, save output.
    Optimized with:
    - Batching of comment crawls (5-10 URLs per API call)
    - Enhanced quality scoring and spam detection
    - Additional metadata for NLP analysis
    """
    if len(seeds) == 0:
        print("No video seeds. Stop.")
        return

    rows = []
    comment_rejection_log = []
    
    # Batch comment crawls for efficiency (Phase 3 optimization)
    video_urls_batch = []
    seed_mapping = {}  # Map video URL -> seed data for batching

    print("\n[INFO] Batching comment crawls for API efficiency...")
    
    for seed_index, (_, seed) in enumerate(seeds.iterrows()):
        video_url = canonical_url(seed["video_url"])
        video_urls_batch.append(video_url)
        seed_mapping[video_url] = seed

        # Process batch when reaches BATCH_COMMENT_URLS or at end
        if len(video_urls_batch) >= BATCH_COMMENT_URLS or seed_index == len(seeds) - 1:
            print(f"[COMMENTS] Crawling batch of {len(video_urls_batch)} videos...")
            
            try:
                videos = crawl_comments(video_urls_batch)

                for video in videos:
                    video_url_result = canonical_url(video.get("webVideoUrl", ""))
                    if video_url_result not in seed_mapping:
                        continue

                    seed = seed_mapping[video_url_result]
                    comments = get_comments_from_video(video)

                    for comment in comments:
                        STATS["comments_total"] += 1
                        
                        comment_text = get_comment_text(comment)
                        if not comment_text.strip():
                            STATS["comments_by_filter"]["empty_text"] += 1
                            comment_rejection_log.append({
                                "place_id": seed["place_id"],
                                "video_url": video_url_result,
                                "rejection_reason": "empty_text"
                            })
                            continue

                        # Detect replies from owner/shop
                        comment_author = get_author_username(comment)
                        video_author = seed.get("author", "")
                        
                        is_owner_reply = is_reply_from_owner(comment_author, video_author)
                        is_greeting_reply = is_reply_greeting(comment_text)
                        
                        # Filter: reply from shop owner (not a real review)
                        if is_owner_reply or is_greeting_reply:
                            STATS["comments_by_filter"]["owner_reply"] += 1
                            comment_rejection_log.append({
                                "place_id": seed["place_id"],
                                "video_url": video_url_result,
                                "rejection_reason": "owner_reply"
                            })
                            continue

                        # Apply quality checks
                        text_quality_score = comment_quality_score(comment_text)
                        is_spam = is_likely_spam(comment_text)
                        language_detected = detect_comment_language(comment_text)
                        emoji_ratio_val = emoji_ratio(comment_text)

                        # Filter: too low quality
                        if text_quality_score < 0.2:
                            STATS["comments_by_filter"]["low_quality"] += 1
                            comment_rejection_log.append({
                                "place_id": seed["place_id"],
                                "video_url": video_url_result,
                                "rejection_reason": f"low_quality_{text_quality_score}"
                            })
                            continue

                        # Filter: likely spam
                        if is_spam:
                            STATS["comments_by_filter"]["spam"] += 1
                            comment_rejection_log.append({
                                "place_id": seed["place_id"],
                                "video_url": video_url_result,
                                "rejection_reason": "likely_spam"
                            })
                            continue

                        # NOTE: Language detection is applied but NOT used for filtering
                        # (teencode and Vietnamese slang variants would be missed)
                        # Language field is kept for optional post-processing filtering

                        useful = is_useful_comment(comment_text, seed["place_name"])

                        comment_id = (
                            comment.get("id")
                            or comment.get("commentId")
                            or comment.get("cid")
                            or comment.get("awemeId")
                            or ""
                        )

                        rows.append({
                            "id": make_id(seed["place_id"], video_url_result, comment_id, comment_text),
                            "platform": "tiktok",
                            "place_id": seed["place_id"],
                            "place_name": seed["place_name"],
                            "place_category": seed.get("place_category", ""),
                            "place_address": seed.get("place_address", ""),
                            "query": seed["query"],
                            "video_url": video_url_result,
                            "video_caption": seed["caption"],
                            "video_views": seed["views"],
                            "video_likes": seed["likes"],
                            "video_comment_count": seed["comment_count"],
                            "comment_id": comment_id,
                            "comment_text": comment_text,
                            "comment_author": comment_author,
                            "comment_likes": comment.get("diggCount") or comment.get("likeCount") or 0,
                            "comment_created_at": (
                                comment.get("createTimeISO")
                                or comment.get("createdAt")
                                or comment.get("createTime")
                                or ""
                            ),
                            "is_useful_comment": useful,
                            "comment_text_quality_score": text_quality_score,
                            "comment_is_likely_spam": is_spam,
                            "comment_is_reply": False,  # Only keep non-replies here
                            "comment_language": language_detected,
                            "comment_emoji_ratio": round(emoji_ratio_val, 3),
                            "scraped_at": datetime.now().isoformat()
                        })

                time.sleep(SLEEP_SECONDS)

            except Exception as e:
                print(f"[FAILED COMMENTS] Batch {video_urls_batch} | {e}")
            
            # Reset batch
            video_urls_batch = []

    comments_df = pd.DataFrame(rows)

    if len(comments_df) > 0:
        comments_df = comments_df.drop_duplicates(subset=["id"])

    comments_df = save_csv(
        comments_df,
        COMMENTS_OUTPUT_FILE,
        append=append_output,
        dedupe_subset=["id"],
    )

    # Log rejection reasons
    if comment_rejection_log:
        rejection_df = pd.DataFrame(comment_rejection_log)
        rejection_csv = COMMENT_REJECTIONS_FILE
        rejection_df = save_csv(
            rejection_df,
            rejection_csv,
            append=append_output,
            dedupe_subset=["place_id", "video_url", "rejection_reason"],
        )
        print(f"[INFO] Logged {len(rejection_df)} rejected comments: {rejection_csv}")

    print(f"\n[SUMMARY] Comments Stage:")
    print(f"  Total comments found: {STATS['comments_total']}")
    print(f"  Filtered by reason:")
    for reason, count in sorted(STATS["comments_by_filter"].items(), key=lambda x: -x[1]):
        print(f"    - {reason}: {count}")
    print(f"  Final comments saved: {len(comments_df)}")
    print(f"  Saved to: {COMMENTS_OUTPUT_FILE}")

    if len(comments_df) > 0:
        useful_rate = comments_df["is_useful_comment"].mean()
        avg_quality = comments_df["comment_text_quality_score"].mean()
        spam_rate = comments_df["comment_is_likely_spam"].mean()
        reply_rate = comments_df["comment_is_reply"].mean() if "comment_is_reply" in comments_df.columns else 0
        print(f"  Useful comment rate: {useful_rate:.2%}")
        print(f"  Avg quality score: {avg_quality:.2f}")
        print(f"  Spam rate: {spam_rate:.2%}")
        print(f"  Reply rate: {reply_rate:.2%}")
        
        # Language distribution (for reference only)
        lang_dist = comments_df["comment_language"].value_counts()
        print(f"  Language distribution:")
        for lang, count in lang_dist.items():
            print(f"    - {lang}: {count}")

    print(f"\n[TELEMETRY]")
    print(f"  Total API calls: {STATS['api_calls']}")
    print(f"  Videos searched: {STATS['videos_searched']}")
    print(f"  Videos selected: {STATS['videos_selected']}")
    print(f"  Comments processed: {STATS['comments_total']}")

    return comments_df


def make_run_id(prefix):
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def append_jsonl(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            count += 1
    return count


def read_jsonl_file(path):
    rows = []
    path = Path(path)
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def latest_jsonl_file(directory):
    directory = Path(directory)
    files = sorted(directory.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def read_jsonl_inputs(directory, raw_file=None, latest=False):
    if raw_file:
        path = Path(raw_file)
        return read_jsonl_file(path), [path]

    if latest:
        path = latest_jsonl_file(directory)
        if path is None:
            return [], []
        return read_jsonl_file(path), [path]

    rows = []
    directory = Path(directory)
    if not directory.exists():
        return rows, []
    files = sorted(directory.glob("*.jsonl"))
    for path in files:
        rows.extend(read_jsonl_file(path))
    return rows, files


def read_jsonl_dir(directory):
    rows, _files = read_jsonl_inputs(directory)
    return rows


def crawl_videos_raw(args):
    all_places = pd.read_csv(args.places_file)
    places = select_places_slice(
        all_places,
        start_row=args.start_row,
        end_row=args.end_row,
        limit=args.limit,
    )
    run_id = args.run_id or make_run_id("tiktok_videos")
    raw_path = TIKTOK_RAW_VIDEO_DIR / f"{run_id}.jsonl"
    rows = []

    print(f"[TIKTOK VIDEOS] Selected places: {len(places)}")
    print(f"[TIKTOK VIDEOS] Raw output: {raw_path}")

    for _, place in places.iterrows():
        place_meta = {
            "place_id": clean_text(place.get("place_id", "")),
            "place_name": clean_text(place.get("title", "")),
            "place_category": clean_text(place.get("category", "")),
            "place_address": clean_text(place.get("address", "")),
        }
        for query in build_queries(place_meta["place_name"], place_meta["place_category"]):
            print(f"[TIKTOK VIDEOS] {place_meta['place_id']} | {query}")
            if args.dry_run:
                continue
            try:
                videos = search_videos(query)
                for video in videos:
                    rows.append({
                        "run_id": run_id,
                        "platform": "tiktok",
                        "stage": "videos",
                        "query": query,
                        **place_meta,
                        "raw_item": video,
                        "scraped_at": datetime.now().isoformat(),
                    })
                time.sleep(args.sleep_seconds)
            except Exception as exc:
                print(f"[FAILED TIKTOK VIDEO SEARCH] {place_meta['place_id']} | {query} | {exc}")

    if not args.dry_run:
        print(f"[TIKTOK VIDEOS] Raw rows saved: {append_jsonl(rows, raw_path)}")
        print(f"[TIKTOK VIDEOS] Next process command:")
        print(f"python src\\innostar\\data_scraping\\tiktok.py process-videos --raw-file \"{raw_path}\"")
    if args.process and not args.dry_run:
        args.raw_file = raw_path
        args.latest = False
        process_videos_raw(args)


def process_videos_raw(args):
    raw_rows, input_files = read_jsonl_inputs(
        args.raw_dir,
        raw_file=args.raw_file,
        latest=args.latest,
    )
    if not raw_rows:
        if Path(VIDEO_SEEDS_FILE).exists():
            print(f"[TIKTOK VIDEOS] No raw rows found. Existing output kept: {VIDEO_SEEDS_FILE}")
            return
        raise FileNotFoundError(f"No raw rows found in {args.raw_dir}")

    print("[TIKTOK VIDEOS] Processing raw inputs:")
    for path in input_files:
        print(f"  - {path}")
    print(f"[TIKTOK VIDEOS] Raw video rows: {len(raw_rows)}")

    candidates_by_query = defaultdict(list)
    rejections = []
    for row in raw_rows:
        video = row.get("raw_item") or {}
        video_url = canonical_url(video.get("webVideoUrl", ""))
        if not video_url:
            continue

        place_id = clean_text(row.get("place_id", ""))
        place_name = clean_text(row.get("place_name", ""))
        query = clean_text(row.get("query", ""))
        comment_count = safe_int(video.get("commentCount", 0))
        if comment_count < args.min_video_comments:
            rejections.append({
                "place_id": place_id,
                "query": query,
                "video_url": video_url,
                "rejection_reason": f"too_few_comments_{comment_count}",
                "relevance_score": "",
                "scraped_at": row.get("scraped_at", ""),
            })
            continue

        score = video_relevance_score(video, place_name, query)
        if score < args.min_relevance_score:
            rejections.append({
                "place_id": place_id,
                "query": query,
                "video_url": video_url,
                "rejection_reason": f"low_relevance_{score}",
                "relevance_score": score,
                "scraped_at": row.get("scraped_at", ""),
            })
            continue

        candidates_by_query[(place_id, query)].append({
            "platform": "tiktok",
            "place_id": place_id,
            "place_name": place_name,
            "place_category": clean_text(row.get("place_category", "")),
            "place_address": clean_text(row.get("place_address", "")),
            "query": query,
            "video_id": video.get("id", ""),
            "video_url": video_url,
            "caption": clean_text(video.get("text", "")),
            "created_at": video.get("createTimeISO", ""),
            "author": (video.get("authorMeta") or {}).get("name", ""),
            "views": safe_int(video.get("playCount", 0)),
            "likes": safe_int(video.get("diggCount", 0)),
            "shares": safe_int(video.get("shareCount", 0)),
            "comment_count": comment_count,
            "relevance_score": score,
            "scraped_at": row.get("scraped_at") or datetime.now().isoformat(),
        })

    selected = []
    place_counts = defaultdict(int)
    for (place_id, _query), candidates in candidates_by_query.items():
        candidates = sorted(
            candidates,
            key=lambda x: (x["relevance_score"], x["comment_count"], x["views"]),
            reverse=True,
        )[:args.max_seed_videos_per_query]
        remaining = args.max_seed_videos_total_per_place - place_counts[place_id]
        selected.extend(candidates[:max(remaining, 0)])
        place_counts[place_id] += len(candidates[:max(remaining, 0)])

    seeds = pd.DataFrame(selected)
    if len(seeds) > 0:
        seeds["dedupe_key"] = seeds["video_url"].apply(lambda x: f"tiktok|{canonical_url(x)}")
        seeds = seeds.sort_values(by=["relevance_score", "comment_count", "views"], ascending=[False, False, False])
        seeds = seeds.drop_duplicates(subset=["dedupe_key"], keep="first").drop(columns=["dedupe_key"])

    save_csv(seeds, VIDEO_CANDIDATES_FILE, append=False, dedupe_subset=["video_url"])
    saved = save_csv(seeds, VIDEO_SEEDS_FILE, append=args.append_output, dedupe_subset=["video_url"])
    if rejections:
        save_csv(pd.DataFrame(rejections), VIDEO_REJECTIONS_FILE, append=args.append_output, dedupe_subset=["place_id", "query", "video_url", "rejection_reason"])

    print(f"[TIKTOK VIDEOS] Seeds total: {len(saved)}")
    print(f"[TIKTOK VIDEOS] Output: {VIDEO_SEEDS_FILE}")


def crawl_comments_raw(args):
    seeds = pd.read_csv(args.seeds_file)
    if args.limit_videos:
        seeds = seeds.head(args.limit_videos)
    run_id = args.run_id or make_run_id("tiktok_comments")
    raw_path = TIKTOK_RAW_COMMENT_DIR / f"{run_id}.jsonl"
    rows = []

    for start in range(0, len(seeds), args.batch_size):
        batch = seeds.iloc[start:start + args.batch_size]
        urls = [canonical_url(url) for url in batch["video_url"].tolist() if canonical_url(url)]
        if not urls:
            continue
        print(f"[TIKTOK COMMENTS] Batch {start // args.batch_size + 1} | videos={len(urls)}")
        if args.dry_run:
            continue
        try:
            videos = crawl_comments(urls)
            seed_records = batch.to_dict(orient="records")
            for video in videos:
                raw_comments = get_comments_from_video(video)
                rows.append({
                    "run_id": run_id,
                    "platform": "tiktok",
                    "stage": "comments",
                    "seeds": seed_records,
                    "raw_item": video,
                    "raw_comments": raw_comments,
                    "raw_comments_count": len(raw_comments),
                    "scraped_at": datetime.now().isoformat(),
                })
            time.sleep(args.sleep_seconds)
        except Exception as exc:
            print(f"[FAILED TIKTOK COMMENTS] {urls} | {exc}")

    if not args.dry_run:
        print(f"[TIKTOK COMMENTS] Raw rows saved: {append_jsonl(rows, raw_path)}")
        print(f"[TIKTOK COMMENTS] Next process command:")
        print(f"python src\\innostar\\data_scraping\\tiktok.py process-comments --raw-file \"{raw_path}\"")
    if args.process and not args.dry_run:
        args.raw_file = raw_path
        args.latest = False
        process_comments_raw(args)


def find_seed_for_raw_video(raw_row):
    seeds = raw_row.get("seeds") or []
    if not seeds:
        return None, ""
    video = raw_row.get("raw_item") or {}
    video_url = canonical_url(video.get("webVideoUrl", ""))
    for seed in seeds:
        if canonical_url(seed.get("video_url", "")) == video_url:
            return seed, video_url
    if len(seeds) == 1:
        return seeds[0], video_url
    return None, video_url


def process_comments_raw(args):
    raw_rows, input_files = read_jsonl_inputs(
        args.raw_dir,
        raw_file=args.raw_file,
        latest=args.latest,
    )
    if not raw_rows:
        if Path(COMMENTS_OUTPUT_FILE).exists():
            print(f"[TIKTOK COMMENTS] No raw rows found. Existing output kept: {COMMENTS_OUTPUT_FILE}")
            return
        raise FileNotFoundError(f"No raw rows found in {args.raw_dir}")

    print("[TIKTOK COMMENTS] Processing raw inputs:")
    for path in input_files:
        print(f"  - {path}")
    print(f"[TIKTOK COMMENTS] Raw comment video rows: {len(raw_rows)}")

    rows = []
    rejection_log = []
    for raw_row in raw_rows:
        seed, video_url_result = find_seed_for_raw_video(raw_row)
        if seed is None:
            continue
        comments = raw_row.get("raw_comments")
        if not isinstance(comments, list):
            if args.fetch_missing_datasets:
                comments = get_comments_from_video(raw_row.get("raw_item") or {})
            else:
                print(
                    "[TIKTOK COMMENTS] Raw row has no raw_comments. "
                    "Skip it, or rerun with --fetch-missing-datasets for old raw files."
                )
                comments = []
        for comment in comments:
            comment_text = get_comment_text(comment)
            if not comment_text.strip():
                rejection_log.append({"place_id": seed["place_id"], "video_url": video_url_result, "rejection_reason": "empty_text"})
                continue

            comment_author = get_author_username(comment)
            video_author = seed.get("author", "")
            if is_reply_from_owner(comment_author, video_author) or is_reply_greeting(comment_text):
                rejection_log.append({"place_id": seed["place_id"], "video_url": video_url_result, "rejection_reason": "owner_reply"})
                continue

            text_quality_score = comment_quality_score(comment_text)
            is_spam = is_likely_spam(comment_text)
            if text_quality_score < args.min_quality_score:
                rejection_log.append({"place_id": seed["place_id"], "video_url": video_url_result, "rejection_reason": f"low_quality_{text_quality_score}"})
                continue
            if is_spam:
                rejection_log.append({"place_id": seed["place_id"], "video_url": video_url_result, "rejection_reason": "likely_spam"})
                continue

            comment_id = comment.get("id") or comment.get("commentId") or comment.get("cid") or comment.get("awemeId") or ""
            rows.append({
                "id": make_id(seed["place_id"], video_url_result, comment_id, comment_text),
                "platform": "tiktok",
                "place_id": seed["place_id"],
                "place_name": seed["place_name"],
                "place_category": seed.get("place_category", ""),
                "place_address": seed.get("place_address", ""),
                "query": seed["query"],
                "video_url": video_url_result,
                "video_caption": seed["caption"],
                "video_views": seed["views"],
                "video_likes": seed["likes"],
                "video_comment_count": seed["comment_count"],
                "comment_id": comment_id,
                "comment_text": comment_text,
                "comment_author": comment_author,
                "comment_likes": comment.get("diggCount") or comment.get("likeCount") or 0,
                "comment_created_at": comment.get("createTimeISO") or comment.get("createdAt") or comment.get("createTime") or "",
                "is_useful_comment": is_useful_comment(comment_text, seed["place_name"]),
                "comment_text_quality_score": text_quality_score,
                "comment_is_likely_spam": is_spam,
                "comment_is_reply": False,
                "comment_language": detect_comment_language(comment_text),
                "comment_emoji_ratio": round(emoji_ratio(comment_text), 3),
                "scraped_at": raw_row.get("scraped_at") or datetime.now().isoformat(),
            })

    comments_df = pd.DataFrame(rows)
    if len(comments_df) > 0:
        comments_df = comments_df.drop_duplicates(subset=["id"])
    elif Path(COMMENTS_OUTPUT_FILE).exists() and not args.append_output:
        print(
            f"[TIKTOK COMMENTS] No processable comments found. "
            f"Existing output kept: {COMMENTS_OUTPUT_FILE}"
        )
        return

    save_csv(comments_df, COMMENT_CANDIDATES_FILE, append=False, dedupe_subset=["id"])
    saved = save_csv(comments_df, COMMENTS_OUTPUT_FILE, append=args.append_output, dedupe_subset=["id"])
    if rejection_log:
        save_csv(pd.DataFrame(rejection_log), COMMENT_REJECTIONS_FILE, append=args.append_output, dedupe_subset=["place_id", "video_url", "rejection_reason"])
    print(f"[TIKTOK COMMENTS] Rows total: {len(saved)}")
    print(f"[TIKTOK COMMENTS] Output: {COMMENTS_OUTPUT_FILE}")


# =====================
# MAIN
# =====================

def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "TikTok crawling pipeline. Select a chunk from the master CSV "
            "using 1-based data row numbers."
        )
    )
    sub = parser.add_subparsers(dest="command")

    crawl_videos = sub.add_parser("crawl-videos", help="Crawl raw TikTok video discovery results.")
    crawl_videos.add_argument("--places-file", default=PLACES_FILE)
    crawl_videos.add_argument("--start-row", type=int, default=1)
    crawl_videos.add_argument("--end-row", type=int, default=None)
    crawl_videos.add_argument("--limit", type=int, default=50)
    crawl_videos.add_argument("--run-id", default="")
    crawl_videos.add_argument("--sleep-seconds", type=int, default=SLEEP_SECONDS)
    crawl_videos.add_argument("--dry-run", action="store_true")
    crawl_videos.add_argument("--process", action="store_true")
    crawl_videos.add_argument("--append-output", action="store_true")
    crawl_videos.set_defaults(
        func=crawl_videos_raw,
        raw_dir=TIKTOK_RAW_VIDEO_DIR,
        min_video_comments=15,
        min_relevance_score=MIN_RELEVANCE_SCORE,
        max_seed_videos_per_query=2,
        max_seed_videos_total_per_place=5,
    )

    process_videos = sub.add_parser("process-videos", help="Process raw TikTok videos into seed output.")
    process_videos.add_argument("--raw-dir", default=TIKTOK_RAW_VIDEO_DIR)
    process_videos.add_argument("--raw-file", default="", help="Process one specific raw video JSONL file.")
    process_videos.add_argument("--latest", action="store_true", help="Process only the newest raw video JSONL file.")
    process_videos.add_argument("--min-video-comments", type=int, default=15)
    process_videos.add_argument("--min-relevance-score", type=float, default=MIN_RELEVANCE_SCORE)
    process_videos.add_argument("--max-seed-videos-per-query", type=int, default=2)
    process_videos.add_argument("--max-seed-videos-total-per-place", type=int, default=5)
    process_videos.add_argument("--append-output", action="store_true")
    process_videos.set_defaults(func=process_videos_raw)

    crawl_comments_parser = sub.add_parser("crawl-comments", help="Crawl raw TikTok comments from seed videos.")
    crawl_comments_parser.add_argument("--seeds-file", default=VIDEO_SEEDS_FILE)
    crawl_comments_parser.add_argument("--limit-videos", type=int, default=None)
    crawl_comments_parser.add_argument("--batch-size", type=int, default=BATCH_COMMENT_URLS)
    crawl_comments_parser.add_argument("--sleep-seconds", type=int, default=SLEEP_SECONDS)
    crawl_comments_parser.add_argument("--run-id", default="")
    crawl_comments_parser.add_argument("--dry-run", action="store_true")
    crawl_comments_parser.add_argument("--process", action="store_true")
    crawl_comments_parser.add_argument("--append-output", action="store_true")
    crawl_comments_parser.set_defaults(
        func=crawl_comments_raw,
        raw_dir=TIKTOK_RAW_COMMENT_DIR,
        min_quality_score=0.2,
    )

    process_comments_parser = sub.add_parser("process-comments", help="Process raw TikTok comments into clean output.")
    process_comments_parser.add_argument("--raw-dir", default=TIKTOK_RAW_COMMENT_DIR)
    process_comments_parser.add_argument("--raw-file", default="", help="Process one specific raw comment JSONL file.")
    process_comments_parser.add_argument("--latest", action="store_true", help="Process only the newest raw comment JSONL file.")
    process_comments_parser.add_argument("--min-quality-score", type=float, default=0.2)
    process_comments_parser.add_argument(
        "--fetch-missing-datasets",
        action="store_true",
        help="For old raw files without raw_comments, fetch commentsDatasetUrl during process.",
    )
    process_comments_parser.add_argument("--append-output", action="store_true")
    process_comments_parser.set_defaults(func=process_comments_raw)

    parser.add_argument(
        "--places-file",
        default=PLACES_FILE,
        help=f"Master places CSV file. Default: {PLACES_FILE}",
    )
    parser.add_argument(
        "--start-row",
        type=int,
        default=1,
        help="1-based data row to start from. Row 1 is the first row after the CSV header.",
    )
    parser.add_argument(
        "--end-row",
        type=int,
        default=None,
        help="1-based data row to end at, inclusive.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Number of places to crawl from --start-row. "
            f"If omitted with no --end-row, defaults to MAX_PLACES={MAX_PLACES}."
        ),
    )
    parser.add_argument(
        "--append-output",
        action="store_true",
        help="Append/dedupe this run into existing output CSV files instead of replacing them.",
    )

    args = parser.parse_args()

    if args.end_row is not None and args.limit is not None:
        parser.error("Use either --end-row or --limit, not both.")

    return args


def main():
    args = parse_args()

    if hasattr(args, "func"):
        args.func(args)
        return

    print("=" * 60)
    print("TikTok Pipeline - OPTIMIZED VERSION")
    print("=" * 60)
    print(f"Start time: {datetime.now().isoformat()}\n")
    
    seeds = create_video_seeds(
        places_file=args.places_file,
        start_row=args.start_row,
        end_row=args.end_row,
        limit=args.limit,
        append_output=args.append_output,
    )
    create_comments_output(seeds, append_output=args.append_output)
    
    print("\n" + "=" * 60)
    print("Pipeline completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
