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

FACEBOOK_POSTS_ACTOR_ID = "apify/facebook-posts-scraper"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs" / "facebook"
SOURCES_FILE = str(Path(OUTPUT_DIR) / "facebook_sources.csv")
POST_SEEDS_FILE = str(Path(OUTPUT_DIR) / "facebook_post_seeds.csv")

RESULTS_LIMIT_PER_SOURCE = 30
ONLY_POSTS_NEWER_THAN = "12 months"

SOURCE_BATCH_SIZE = 1
SLEEP_SECONDS = 2

MIN_POST_COMMENTS = 5
MIN_POST_RELEVANCE_SCORE = 3.5

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
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


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
        df = df.drop_duplicates(subset=dedupe_subset, keep="last")

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return df


# =====================
# FIELD EXTRACTION
# =====================

def get_first(item, keys, default=""):
    for key in keys:
        value = item.get(key)
        if value not in [None, ""]:
            return value
    return default


def extract_post_url(item):
    return canonical_facebook_url(get_first(item, [
        "url",
        "postUrl",
        "post_url",
        "facebookUrl",
        "link",
        "topLevelUrl"
    ]))


def extract_post_id(item, post_url):
    post_id = get_first(item, [
        "postId",
        "post_id",
        "id",
        "legacyId"
    ])

    if post_id:
        return clean_text(post_id)

    return make_id(post_url)


def extract_post_text(item):
    text = get_first(item, [
        "text",
        "caption",
        "message",
        "description",
        "postText",
        "title"
    ])

    return clean_text(text)


def extract_created_at(item):
    return clean_text(get_first(item, [
        "time",
        "timestamp",
        "createdAt",
        "created_at",
        "date",
        "publishTime",
        "publishedAt"
    ]))


def extract_author_name(item):
    author = item.get("author") or item.get("page") or {}

    if isinstance(author, dict):
        return clean_text(
            author.get("name")
            or author.get("title")
            or author.get("username")
            or author.get("id")
        )

    return clean_text(
        get_first(item, ["authorName", "pageName", "userName"], "")
    )


def extract_likes(item):
    return safe_int(get_first(item, [
        "likes",
        "likesCount",
        "reactionCount",
        "reactionsCount"
    ], 0))


def extract_comments_count(item):
    return safe_int(get_first(item, [
        "comments",
        "commentsCount",
        "commentCount",
        "comments_count"
    ], 0))


def extract_shares(item):
    return safe_int(get_first(item, [
        "shares",
        "sharesCount",
        "shareCount"
    ], 0))


# =====================
# POST FILTERING
# =====================

def is_bad_post_text(text):
    t = normalize_text(text)

    bad_terms = [
        "tuyển dụng",
        "tuyen dung",
        "minigame",
        "giveaway",
        "chốt đơn",
        "chot don",
        "livestream",
        "sale",
        "giảm giá",
        "giam gia",
        "voucher",
        "combo",
        "đặt tour",
        "dat tour",
        "booking",
        "inbox",
        "ib ngay",
        "liên hệ",
        "lien he",
        "zalo",
        "khuyến mãi",
        "khuyen mai",
    ]

    return any(term in t for term in bad_terms)


def post_relevance_score(post_text, place_name, source_title="", source_snippet=""):
    text_norm = normalize_text(post_text)
    place_norm = normalize_text(place_name)
    source_norm = normalize_text(f"{source_title} {source_snippet}")

    score = 0.0

    if place_norm and place_norm in text_norm:
        score += 4.0

    if "đà lạt" in text_norm or "da lat" in text_norm or "dalat" in text_norm:
        score += 2.0

    # Nếu source title/snippet đã match place, post từ source đó vẫn có chút điểm
    if place_norm and place_norm in source_norm:
        score += 1.5

    useful_context_terms = [
        "review",
        "trải nghiệm",
        "trai nghiem",
        "check in",
        "đi rồi",
        "di roi",
        "quán",
        "quan",
        "cafe",
        "du lịch",
        "du lich",
        "ăn",
        "an",
        "ngon",
        "đẹp",
        "dep",
        "giá",
        "gia",
    ]

    matched_context = sum(1 for term in useful_context_terms if term in text_norm)
    score += min(2.0, matched_context * 0.5)

    if is_bad_post_text(post_text):
        score -= 2.5

    return round(max(0, score), 2)


def should_keep_post(post, source):
    post_url = post["post_url"]
    post_text = post["post_text"]
    comments_count = post["comments_count"]
    relevance_score = post["post_relevance_score"]

    if not post_url:
        return False, "missing_post_url"

    if comments_count < MIN_POST_COMMENTS:
        return False, "too_few_comments"

    if relevance_score < MIN_POST_RELEVANCE_SCORE:
        return False, "low_relevance"

    if len(normalize_text(post_text)) < 10:
        return False, "too_short_text"

    return True, ""


# =====================
# APIFY
# =====================

def run_facebook_posts_actor(source_urls):
    actor_input = {
        "startUrls": [{"url": url} for url in source_urls],
        "resultsLimit": RESULTS_LIMIT_PER_SOURCE,
        "onlyPostsNewerThan": ONLY_POSTS_NEWER_THAN,
    }

    run = client.actor(FACEBOOK_POSTS_ACTOR_ID).call(run_input=actor_input)
    dataset_id = run.get("defaultDatasetId")

    if not dataset_id:
        return []

    return list(client.dataset(dataset_id).iterate_items())


# =====================
# MAIN PIPELINE
# =====================

def parse_place_ids(value):
    if not value:
        return []

    return [clean_text(x) for x in str(value).split(",") if clean_text(x)]


def prepare_sources(sources, limit=None, include_groups=False, place_ids=None):
    df = sources.copy()

    if place_ids:
        df = df[df["place_id"].astype(str).isin(place_ids)]

    df = df[df["next_stage"].astype(str) == "posts_scrape"]

    if not include_groups:
        df = df[df["source_type"].isin(["page", "profile"])]

    df["source_url"] = df["source_url"].apply(canonical_facebook_url)
    df = df[df["source_url"] != ""]

    df = df.sort_values(
        by=["source_score"],
        ascending=False
    )

    df = df.drop_duplicates(subset=["source_id"], keep="first")

    if limit:
        df = df.head(limit)

    return df


def create_post_seeds(sources, append=False):
    rows = []
    reject_rows = []

    source_batches = [
        sources.iloc[i:i + SOURCE_BATCH_SIZE]
        for i in range(0, len(sources), SOURCE_BATCH_SIZE)
    ]

    for batch_index, batch in enumerate(source_batches, start=1):
        urls = batch["source_url"].tolist()

        print(f"[POSTS] Batch {batch_index}/{len(source_batches)} | sources={len(urls)}")

        source_map = {
            canonical_facebook_url(row["source_url"]): row.to_dict()
            for _, row in batch.iterrows()
        }

        try:
            items = run_facebook_posts_actor(urls)

            for item in items:
                post_url = extract_post_url(item)

                # Actor output đôi khi không trả source URL rõ.
                # Fallback: nếu chỉ batch 1 URL, map trực tiếp source đó.
                source = None

                item_source_url = canonical_facebook_url(get_first(item, [
                    "facebookUrl",
                    "pageUrl",
                    "sourceUrl",
                    "inputUrl",
                    "url"
                ]))

                if item_source_url in source_map:
                    source = source_map[item_source_url]
                elif len(source_map) == 1:
                    source = list(source_map.values())[0]
                else:
                    # fallback match theo source_url prefix
                    for s_url, s in source_map.items():
                        if s_url and s_url in clean_text(item):
                            source = s
                            break

                if source is None:
                    # Không biết post thuộc place nào thì bỏ để tránh sai mapping.
                    reject_rows.append({
                        "source_url": item_source_url,
                        "post_url": post_url,
                        "reject_reason": "cannot_map_source",
                        "scraped_at": datetime.now().isoformat(),
                    })
                    continue

                place_id = clean_text(source.get("place_id", ""))
                place_name = clean_text(source.get("place_name", ""))

                post_text = extract_post_text(item)
                comments_count = extract_comments_count(item)
                score = post_relevance_score(
                    post_text=post_text,
                    place_name=place_name,
                    source_title=source.get("source_title", ""),
                    source_snippet=source.get("source_snippet", ""),
                )

                post = {
                    "post_seed_id": make_id(place_id, post_url),
                    "platform": "facebook",
                    "place_id": place_id,
                    "place_name": place_name,
                    "source_id": clean_text(source.get("source_id", "")),
                    "source_url": clean_text(source.get("source_url", "")),
                    "source_type": clean_text(source.get("source_type", "")),
                    "post_id": extract_post_id(item, post_url),
                    "post_url": post_url,
                    "post_text": post_text,
                    "created_at": extract_created_at(item),
                    "author_name": extract_author_name(item),
                    "likes": extract_likes(item),
                    "comments_count": comments_count,
                    "shares": extract_shares(item),
                    "post_relevance_score": score,
                    "status": "new",
                    "scraped_at": datetime.now().isoformat(),
                }

                keep, reason = should_keep_post(post, source)

                if keep:
                    rows.append(post)
                else:
                    reject_rows.append({
                        "place_id": place_id,
                        "place_name": place_name,
                        "source_id": clean_text(source.get("source_id", "")),
                        "source_url": clean_text(source.get("source_url", "")),
                        "post_url": post_url,
                        "post_text": post_text,
                        "comments_count": comments_count,
                        "post_relevance_score": score,
                        "reject_reason": reason,
                        "scraped_at": datetime.now().isoformat(),
                    })

            time.sleep(SLEEP_SECONDS)

        except Exception as e:
            print(f"[FAILED POSTS BATCH] {batch_index} | {e}")

            for _, s in batch.iterrows():
                reject_rows.append({
                    "source_id": clean_text(s.get("source_id", "")),
                    "source_url": clean_text(s.get("source_url", "")),
                    "reject_reason": f"actor_failed: {e}",
                    "scraped_at": datetime.now().isoformat(),
                })

            continue

    seeds = pd.DataFrame(rows)

    if len(seeds) > 0:
        seeds = seeds.sort_values(
            by=["post_relevance_score", "comments_count", "likes"],
            ascending=[False, False, False]
        )
        seeds = seeds.drop_duplicates(subset=["place_id", "post_url"], keep="first")

    saved = save_output(
        seeds,
        POST_SEEDS_FILE,
        append=append,
        dedupe_subset=["place_id", "post_url"]
    )

    reject_file = str(Path(OUTPUT_DIR) / "facebook_post_rejections.csv")
    if len(reject_rows) > 0:
        reject_df = pd.DataFrame(reject_rows)
        save_output(
            reject_df,
            reject_file,
            append=append,
            dedupe_subset=["source_url", "post_url", "reject_reason"]
        )

    print("\nDone.")
    print(f"Saved post seeds: {POST_SEEDS_FILE}")
    print(f"Post seeds this run: {len(seeds)}")
    print(f"Post seeds total file: {len(saved)}")
    print(f"Reject log: {reject_file}")

    if len(saved) > 0:
        print("\nCoverage:")
        print(f"Places with post seeds: {saved['place_id'].nunique()}")
        print("\nTop places by post count:")
        print(saved["place_name"].value_counts().head(10))


def main():
    global SOURCE_BATCH_SIZE

    parser = argparse.ArgumentParser()

    parser.add_argument("--sources-file", default=SOURCES_FILE)
    parser.add_argument("--limit-sources", type=int, default=None)
    parser.add_argument("--place-ids", default="")
    parser.add_argument("--source-batch-size", type=int, default=SOURCE_BATCH_SIZE)
    parser.add_argument("--include-groups", action="store_true")
    parser.add_argument("--append", action="store_true")

    args = parser.parse_args()
    SOURCE_BATCH_SIZE = args.source_batch_size

    sources_path = Path(args.sources_file)

    if not sources_path.exists():
        raise FileNotFoundError(f"Missing sources file: {sources_path}")

    sources = pd.read_csv(sources_path)

    required_cols = {
        "source_id",
        "place_id",
        "place_name",
        "source_url",
        "source_type",
        "source_score",
        "next_stage",
    }

    missing = required_cols - set(sources.columns)
    if missing:
        raise ValueError(f"Missing columns in facebook_sources.csv: {missing}")

    selected_sources = prepare_sources(
        sources=sources,
        limit=args.limit_sources,
        include_groups=args.include_groups,
        place_ids=parse_place_ids(args.place_ids),
    )

    print(f"Selected sources for post crawling: {len(selected_sources)}")

    if len(selected_sources) == 0:
        print("No valid sources to crawl.")
        return

    create_post_seeds(
        sources=selected_sources,
        append=args.append,
    )


if __name__ == "__main__":
    main()
