import os
import re
import time
import argparse
import hashlib
from pathlib import Path
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from apify_client import ApifyClient


# =====================
# CONFIG
# =====================

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
if not APIFY_TOKEN:
    raise ValueError("Missing APIFY_TOKEN in .env")

FACEBOOK_COMMENTS_ACTOR_ID = "apify/facebook-comments-scraper"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = str(PROJECT_ROOT / "data" / "outputs" / "facebook")

POST_SEEDS_FILE = str(Path(OUTPUT_DIR) / "facebook_post_seeds.csv")
SOURCES_FILE = str(Path(OUTPUT_DIR) / "facebook_sources.csv")
COMMENTS_OUTPUT_FILE = str(Path(OUTPUT_DIR) / "facebook_comments_output.csv")

COMMENTS_LIMIT_PER_POST = 100
INCLUDE_NESTED_COMMENTS = True
VIEW_OPTION = "RANKED_UNFILTERED"

# Để mapping chắc chắn, default batch = 1.
# Sau khi output ổn, có thể tăng lên 3-5.
BATCH_SIZE = 1
SLEEP_SECONDS = 2

MIN_COMMENT_WORDS = 5

client = ApifyClient(APIFY_TOKEN)


# =====================
# HELPERS
# =====================

def clean_text(x):
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()


def normalize_text(x):
    x = clean_text(x).lower()
    x = re.sub(r"http\S+", " ", x)
    x = re.sub(r"[^\w\sÀ-ỹ]", " ", x)
    x = re.sub(r"\s+", " ", x)
    return x.strip()


def make_id(*parts):
    raw = "|".join(clean_text(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def canonical_facebook_url(url):
    url = clean_text(url)
    if not url:
        return ""

    replacements = {
        "http://facebook.com/": "https://www.facebook.com/",
        "https://facebook.com/": "https://www.facebook.com/",
        "http://www.facebook.com/": "https://www.facebook.com/",
        "https://m.facebook.com/": "https://www.facebook.com/",
        "http://m.facebook.com/": "https://www.facebook.com/",
        "https://fb.com/": "https://www.facebook.com/",
        "http://fb.com/": "https://www.facebook.com/",
    }

    for old, new in replacements.items():
        url = url.replace(old, new)

    url = url.split("?")[0]
    url = url.split("#")[0]
    url = url.rstrip("/")

    return url


def read_existing_csv(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def save_output(df, path, append=False, dedupe_subset=None):
    if append:
        old = read_existing_csv(path)
        if len(old) > 0:
            df = pd.concat([old, df], ignore_index=True)

    if len(df) > 0 and dedupe_subset:
        available = [c for c in dedupe_subset if c in df.columns]
        if available:
            df = df.drop_duplicates(subset=available, keep="last")

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return df


def get_first(item, keys, default=""):
    for key in keys:
        value = item.get(key)
        if value not in [None, ""]:
            return value
    return default


# =====================
# COMMENT FIELD EXTRACTION
# =====================

def extract_comment_id(item):
    return clean_text(get_first(item, [
        "commentId",
        "comment_id",
        "id",
        "facebookId",
        "legacyId",
        "url",
        "commentUrl",
    ]))


def extract_comment_text(item):
    return clean_text(get_first(item, [
        "text",
        "comment",
        "commentText",
        "message",
        "content",
        "body",
    ]))


def extract_comment_author(item):
    author = item.get("author") or item.get("commenter") or item.get("user") or {}

    if isinstance(author, dict):
        return clean_text(
            author.get("name")
            or author.get("username")
            or author.get("profileName")
            or author.get("id")
            or ""
        )

    return clean_text(get_first(item, [
        "authorName",
        "commenterName",
        "profileName",
        "userName",
        "name",
    ]))


def extract_comment_author_url(item):
    author = item.get("author") or item.get("commenter") or item.get("user") or {}

    if isinstance(author, dict):
        return clean_text(
            author.get("profileUrl")
            or author.get("url")
            or author.get("profileLink")
            or ""
        )

    return clean_text(get_first(item, [
        "authorUrl",
        "commenterUrl",
        "profileUrl",
        "profileLink",
    ]))


def extract_comment_created_at(item):
    return clean_text(get_first(item, [
        "date",
        "time",
        "timestamp",
        "createdAt",
        "created_at",
        "publishedAt",
    ]))


def extract_comment_likes(item):
    return safe_int(get_first(item, [
        "likes",
        "likesCount",
        "likeCount",
        "reactionCount",
        "reactionsCount",
    ], 0))


def extract_comment_depth(item):
    return safe_int(get_first(item, [
        "threadingDepth",
        "depth",
        "level",
        "replyDepth",
    ], 0))


def extract_comment_post_url(item):
    return canonical_facebook_url(get_first(item, [
        "postUrl",
        "post_url",
        "facebookUrl",
        "url",
        "inputUrl",
        "sourceUrl",
    ]))


# =====================
# COMMENT FILTERING
# =====================

def count_emojis(text):
    if not text:
        return 0

    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001F9FF"
        "\U0001F600-\U0001F64F"
        "\u2600-\u27BF"
        "]+",
        flags=re.UNICODE
    )

    return len(emoji_pattern.findall(text))


def emoji_ratio(text):
    text = clean_text(text)
    if not text:
        return 0
    return count_emojis(text) / max(len(text), 1)


def detect_language_simple(text):
    if not text:
        return "unknown"

    vi_chars = sum(1 for c in text if 192 <= ord(c) <= 7871)
    en_chars = sum(1 for c in text if c.isalpha() and ord(c) < 128)

    total = vi_chars + en_chars
    if total == 0:
        return "unknown"

    if vi_chars / total > 0.45:
        return "vi"

    if en_chars / total > 0.75:
        return "en"

    if vi_chars > 0 and en_chars > 0:
        return "mixed"

    return "other"


def is_owner_or_page_reply(comment_author, post_author):
    a = normalize_text(comment_author)
    p = normalize_text(post_author)

    if not a or not p:
        return False

    if a == p:
        return True

    if len(a) >= 5 and len(p) >= 5:
        if a in p or p in a:
            return True

    return False


def is_greeting_or_page_reply(text):
    t = normalize_text(text)

    greeting_patterns = [
        "cảm ơn bạn",
        "cam on ban",
        "cảm ơn anh",
        "cảm ơn chị",
        "dạ cảm ơn",
        "da cam on",
        "shop cảm ơn",
        "page cảm ơn",
        "inbox shop",
        "check ib",
        "bên em",
        "tụi em",
        "chúng tôi",
        "xin chào",
        "thank you",
        "thanks",
    ]

    if any(p in t for p in greeting_patterns):
        return True

    return False


def is_likely_spam(text):
    t = normalize_text(text)

    if not t:
        return True

    if len(t) < 2:
        return True

    if emoji_ratio(text) > 0.5 and len(t.split()) <= 3:
        return True

    if re.search(r"([a-zàáảãạăằắẳẵặâầấẩẫậ])\1{4,}", t):
        return True

    if t.count("#") > 4:
        return True

    if "http" in t or "www" in t:
        return True

    return False


def comment_quality_score(text):
    text = clean_text(text)

    if not text:
        return 0.0

    score = 0.0
    length = len(text)

    if 40 <= length <= 500:
        score += 0.4
    elif 20 <= length < 40:
        score += 0.25
    elif length > 500:
        score += 0.3

    er = emoji_ratio(text)

    if er < 0.1:
        score += 0.3
    elif er < 0.3:
        score += 0.15

    lang = detect_language_simple(text)
    if lang == "vi":
        score += 0.2
    elif lang == "mixed":
        score += 0.1
    elif lang == "en":
        score += 0.05

    if is_likely_spam(text):
        score -= 0.3

    return round(max(0, min(score, 1.0)), 2)


def classify_comment(text, place_name, comment_author="", post_author=""):
    """
    Return:
    - is_useful_comment
    - reject_reason
    - quality_score
    - language
    """

    text_clean = clean_text(text)
    t = normalize_text(text_clean)

    if not t:
        return False, "empty_text", 0.0, "unknown"

    if is_owner_or_page_reply(comment_author, post_author):
        return False, "owner_or_page_reply", 0.0, detect_language_simple(text_clean)

    if is_greeting_or_page_reply(text_clean):
        return False, "greeting_or_page_reply", 0.0, detect_language_simple(text_clean)

    if is_likely_spam(text_clean):
        return False, "likely_spam", comment_quality_score(text_clean), detect_language_simple(text_clean)

    if len(t.split()) < MIN_COMMENT_WORDS:
        return False, "too_short", comment_quality_score(text_clean), detect_language_simple(text_clean)

    junk_terms = [
        "tag bạn",
        "tag ban",
        "đi không",
        "di khong",
        "kèo này",
        "keo nay",
        "xin địa chỉ",
        "xin dia chi",
        "ở đâu",
        "o dau",
        "xin giá",
        "xin gia",
        "ib",
        "inbox",
        "chấm",
        "hóng",
        " hóng ",
        "rep em",
        "check ib",
        "cho xin",
        "bao nhiêu",
        "bao nhieu",
        "có ship",
        "co ship",
        "sdt",
        "zalo",
    ]

    if any(term in t for term in junk_terms):
        return False, "junk_question_or_tag", comment_quality_score(text_clean), detect_language_simple(text_clean)

    useful_terms = [
        "mình đi",
        "minh di",
        "tui đi",
        "đã đi",
        "da di",
        "vừa đi",
        "vua di",
        "đi rồi",
        "di roi",
        "trải nghiệm",
        "trai nghiem",
        "review",
        "giá",
        "gia",
        "đắt",
        "dat",
        "rẻ",
        "re",
        "mắc",
        "mac",
        "đông",
        "dong",
        "vắng",
        "vang",
        "đẹp",
        "dep",
        "xấu",
        "xau",
        "ngon",
        "dở",
        "do",
        "phục vụ",
        "phuc vu",
        "thái độ",
        "thai do",
        "sạch",
        "sach",
        "bẩn",
        "ban",
        "đáng đi",
        "dang di",
        "không đáng",
        "khong dang",
        "thất vọng",
        "that vong",
        "quay lại",
        "quay lai",
        "không quay lại",
        "ngoài đời",
        "ngoai doi",
        "khác ảnh",
        "khac anh",
        "chặt chém",
        "chat chem",
        "gửi xe",
        "gui xe",
        "vé",
        "kẹt xe",
        "ket xe",
        "đường đi",
        "duong di",
    ]

    matched_terms = sum(1 for term in useful_terms if term in t)
    place_norm = normalize_text(place_name)
    quality = comment_quality_score(text_clean)
    lang = detect_language_simple(text_clean)

    if matched_terms >= 1 and quality >= 0.2:
        return True, "", quality, lang

    if place_norm and place_norm in t and quality >= 0.2:
        return True, "", quality, lang

    return False, "no_review_signal", quality, lang


# =====================
# TARGETS
# =====================

def parse_place_ids(value):
    if not value:
        return []
    return [clean_text(x) for x in str(value).split(",") if clean_text(x)]


def load_comment_targets(limit=None, include_direct=True, place_ids=None):
    targets = []
    place_ids = set(place_ids or [])

    if os.path.exists(POST_SEEDS_FILE):
        posts = pd.read_csv(POST_SEEDS_FILE)

        for _, row in posts.iterrows():
            if place_ids and clean_text(row.get("place_id", "")) not in place_ids:
                continue
            post_url = canonical_facebook_url(row.get("post_url", ""))

            if not post_url:
                continue

            targets.append({
                "target_id": make_id("post_seed", row.get("place_id", ""), post_url),
                "target_origin": "post_seed",
                "place_id": clean_text(row.get("place_id", "")),
                "place_name": clean_text(row.get("place_name", "")),
                "source_url": clean_text(row.get("source_url", "")),
                "post_url": post_url,
                "post_id": clean_text(row.get("post_id", "")),
                "post_text": clean_text(row.get("post_text", "")),
                "post_author": clean_text(row.get("author_name", "")),
                "post_comments_count": safe_int(row.get("comments_count", 0)),
                "post_relevance_score": row.get("post_relevance_score", ""),
            })

    if include_direct and os.path.exists(SOURCES_FILE):
        sources = pd.read_csv(SOURCES_FILE)

        direct = sources[
            sources["next_stage"].astype(str).eq("comments_direct")
        ].copy()

        for _, row in direct.iterrows():
            if place_ids and clean_text(row.get("place_id", "")) not in place_ids:
                continue
            post_url = canonical_facebook_url(row.get("source_url", ""))

            if not post_url:
                continue

            targets.append({
                "target_id": make_id("direct_source", row.get("place_id", ""), post_url),
                "target_origin": "direct_source",
                "place_id": clean_text(row.get("place_id", "")),
                "place_name": clean_text(row.get("place_name", "")),
                "source_url": clean_text(row.get("source_url", "")),
                "post_url": post_url,
                "post_id": "",
                "post_text": clean_text(row.get("source_title", "")),
                "post_author": "",
                "post_comments_count": "",
                "post_relevance_score": row.get("source_score", ""),
            })

    df = pd.DataFrame(targets)

    if len(df) == 0:
        return df

    df = df.drop_duplicates(subset=["post_url"], keep="first")

    # Ưu tiên post seed trước, rồi post nhiều comment
    if "post_comments_count" in df.columns:
        df["post_comments_count_sort"] = df["post_comments_count"].apply(safe_int)
        df = df.sort_values(
            by=["target_origin", "post_comments_count_sort"],
            ascending=[False, False]
        )
        df = df.drop(columns=["post_comments_count_sort"])

    if limit:
        df = df.head(limit)

    return df


# =====================
# APIFY
# =====================

def run_comments_actor(urls):
    actor_input = {
        "startUrls": [{"url": url} for url in urls],
        "resultsLimit": COMMENTS_LIMIT_PER_POST,
        "includeNestedComments": INCLUDE_NESTED_COMMENTS,
        "viewOption": VIEW_OPTION,
    }

    run = client.actor(FACEBOOK_COMMENTS_ACTOR_ID).call(run_input=actor_input)
    dataset_id = run.get("defaultDatasetId")

    if not dataset_id:
        return []

    return list(client.dataset(dataset_id).iterate_items())


# =====================
# MAIN PIPELINE
# =====================

def crawl_comments(targets, append=False):
    rows = []

    batches = [
        targets.iloc[i:i + BATCH_SIZE]
        for i in range(0, len(targets), BATCH_SIZE)
    ]

    for batch_index, batch in enumerate(batches, start=1):
        urls = [canonical_facebook_url(x) for x in batch["post_url"].tolist()]
        urls = [u for u in urls if u]

        if not urls:
            continue

        target_map = {
            canonical_facebook_url(row["post_url"]): row.to_dict()
            for _, row in batch.iterrows()
        }

        print(f"[COMMENTS] Batch {batch_index}/{len(batches)} | urls={len(urls)}")

        try:
            items = run_comments_actor(urls)

            for item in items:
                item_post_url = extract_comment_post_url(item)

                target = None

                if item_post_url in target_map:
                    target = target_map[item_post_url]
                elif len(target_map) == 1:
                    target = list(target_map.values())[0]

                if target is None:
                    # Không map được thì bỏ, tránh gán nhầm place.
                    continue

                comment_text = extract_comment_text(item)
                comment_author = extract_comment_author(item)
                comment_id = extract_comment_id(item)

                is_useful, reject_reason, quality, lang = classify_comment(
                    text=comment_text,
                    place_name=target["place_name"],
                    comment_author=comment_author,
                    post_author=target.get("post_author", ""),
                )

                rows.append({
                    "id": make_id(target["place_id"], target["post_url"], comment_id, comment_text),
                    "platform": "facebook",
                    "place_id": target["place_id"],
                    "place_name": target["place_name"],
                    "target_origin": target["target_origin"],
                    "source_url": target["source_url"],
                    "post_url": target["post_url"],
                    "post_id": target["post_id"],
                    "post_text": target["post_text"],
                    "post_author": target["post_author"],
                    "post_comments_count": target["post_comments_count"],
                    "post_relevance_score": target["post_relevance_score"],
                    "comment_id": comment_id,
                    "comment_text": comment_text,
                    "comment_author": comment_author,
                    "comment_author_url": extract_comment_author_url(item),
                    "comment_likes": extract_comment_likes(item),
                    "comment_created_at": extract_comment_created_at(item),
                    "comment_depth": extract_comment_depth(item),
                    "is_useful_comment": is_useful,
                    "comment_quality_score": quality,
                    "comment_language": lang,
                    "comment_reject_reason": reject_reason,
                    "scraped_at": datetime.now().isoformat(),
                })

            time.sleep(SLEEP_SECONDS)

        except Exception as e:
            print(f"[FAILED COMMENTS BATCH] {batch_index} | {e}")
            continue

    comments_df = pd.DataFrame(rows)

    if len(comments_df) > 0:
        comments_df = comments_df.drop_duplicates(subset=["id"], keep="last")

    saved = save_output(
        comments_df,
        COMMENTS_OUTPUT_FILE,
        append=append,
        dedupe_subset=["id"],
    )

    print("\nDone.")
    print(f"Saved comments: {COMMENTS_OUTPUT_FILE}")
    print(f"Comments this run: {len(comments_df)}")
    print(f"Comments total file: {len(saved)}")

    if len(saved) > 0:
        print("\nCoverage:")
        print(f"Places with comments: {saved['place_id'].nunique()}")
        print(f"Useful comment rate: {saved['is_useful_comment'].mean():.2%}")

        print("\nReject reason summary:")
        print(saved["comment_reject_reason"].fillna("").replace("", "useful").value_counts().head(15))

        print("\nTop places by comment count:")
        print(saved["place_name"].value_counts().head(10))


def main():
    global BATCH_SIZE
    global COMMENTS_LIMIT_PER_POST

    parser = argparse.ArgumentParser()

    parser.add_argument("--limit-posts", type=int, default=None)
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--no-direct-sources", action="store_true")
    parser.add_argument("--place-ids", default="")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--comments-limit", type=int, default=COMMENTS_LIMIT_PER_POST)

    args = parser.parse_args()

    BATCH_SIZE = args.batch_size
    COMMENTS_LIMIT_PER_POST = args.comments_limit

    targets = load_comment_targets(
        limit=args.limit_posts,
        include_direct=not args.no_direct_sources,
        place_ids=parse_place_ids(args.place_ids),
    )

    print(f"Selected comment targets: {len(targets)}")

    if len(targets) == 0:
        print("No comment targets found.")
        return

    crawl_comments(
        targets=targets,
        append=args.append,
    )


if __name__ == "__main__":
    main()
