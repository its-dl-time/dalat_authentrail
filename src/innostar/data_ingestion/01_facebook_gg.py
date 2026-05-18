import os
import re
import time
import argparse
import hashlib
from datetime import datetime
from pathlib import Path

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

GOOGLE_ACTOR_ID = "apify/google-search-scraper"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PLACES_FILE = PROJECT_ROOT / "data" / "processed" / "places_master_top50.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs" / "facebook"
OUTPUT_FILE = "facebook_sources.csv"

MAX_PLACES = 3
QUERIES_PER_PLACE = 2
MAX_PAGES_PER_QUERY = 1
RESULTS_PER_PAGE = 10
QUERY_CHUNK_SIZE = 20
SLEEP_SECONDS = 2

MIN_SOURCE_SCORE = 4

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


def is_facebook_url(url):
    u = clean_text(url).lower()
    return any(x in u for x in [
        "facebook.com",
        "fb.com",
        "m.facebook.com",
        "www.facebook.com",
    ])


def extract_urls_from_text(text):
    text = clean_text(text)
    if not text:
        return []

    return re.findall(r"https?://[^\s,\]\)\"']+", text)


def infer_source_type(url):
    u = url.lower()

    if "/groups/" in u:
        return "group"

    if any(x in u for x in ["/posts/", "/permalink/", "story.php"]):
        return "post"

    if any(x in u for x in ["/reel/", "/reels/"]):
        return "reel"

    if any(x in u for x in ["/videos/", "/watch/"]):
        return "video"

    if "profile.php" in u:
        return "profile"

    if "facebook.com" in u:
        return "page"

    return "unknown"


def is_bad_facebook_url(url):
    u = url.lower()

    bad_patterns = [
        "login",
        "sharer.php",
        "plugins",
        "dialog",
        "privacy",
        "help",
        "recover",
        "unsupportedbrowser",
        "checkpoint",
        "policy",
        "terms",
        "l.php",
    ]

    return any(x in u for x in bad_patterns)


def score_source(url, title, snippet, place_name):
    url_norm = normalize_text(url)
    title_norm = normalize_text(title)
    snippet_norm = normalize_text(snippet)
    place_norm = normalize_text(place_name)

    combined = f"{url_norm} {title_norm} {snippet_norm}"

    score = 0

    if "facebook com" in url_norm:
        score += 2

    if place_norm and place_norm in combined:
        score += 3

    if any(x in combined for x in ["đà lạt", "da lat", "dalat"]):
        score += 2

    source_type = infer_source_type(url)

    if source_type in ["page", "profile"]:
        score += 2

    if source_type in ["post", "reel", "video"]:
        score += 2

    if source_type == "group":
        score += 1

    if is_bad_facebook_url(url):
        score -= 6

    return score


def build_source_row(place_id, place_name, query, url, title="", snippet="", origin="google_search"):
    url = canonical_facebook_url(url)

    if not is_facebook_url(url):
        return None

    if is_bad_facebook_url(url):
        return None

    source_type = infer_source_type(url)
    score = score_source(url, title, snippet, place_name)

    if score < MIN_SOURCE_SCORE:
        return None

    if source_type in ["post", "reel", "video"]:
        next_stage = "comments_direct"
    elif source_type in ["page", "profile", "group"]:
        next_stage = "posts_scrape"
    else:
        next_stage = "manual_review"

    return {
        "source_id": make_id(place_id, url),
        "place_id": place_id,
        "place_name": place_name,
        "query": query,
        "source_url": url,
        "source_type": source_type,
        "source_title": clean_text(title),
        "source_snippet": clean_text(snippet),
        "source_origin": origin,
        "source_score": score,
        "next_stage": next_stage,
        "status": "new",
        "scraped_at": datetime.now().isoformat(),
    }


# =====================
# QUERY GENERATION
# =====================

def build_queries(place_name, category=""):
    category_lower = normalize_text(category)

    base = [
        f'site:facebook.com "{place_name}" "Đà Lạt"',
        f'site:facebook.com "{place_name}" "review"',
    ]

    if any(x in category_lower for x in ["cà phê", "cafe", "quán ăn", "nhà hàng", "restaurant"]):
        base = [
            f'site:facebook.com "{place_name}" "Đà Lạt" "review"',
            f'site:facebook.com "{place_name}" "ngon"',
        ]

    if any(x in category_lower for x in ["du lịch", "tourist", "attraction", "điểm du lịch"]):
        base = [
            f'site:facebook.com "{place_name}" "Đà Lạt" "check in"',
            f'site:facebook.com "{place_name}" "trải nghiệm"',
        ]

    return base[:QUERIES_PER_PLACE]


# =====================
# SOURCE 1: MASTER FILE
# =====================

def collect_sources_from_master(places):
    rows = []

    for _, place in places.iterrows():
        place_id = clean_text(place.get("place_id", ""))
        place_name = clean_text(place.get("title", ""))

        for col in places.columns:
            value = clean_text(place.get(col, ""))

            if not value:
                continue

            candidates = []

            if is_facebook_url(value):
                candidates.append(value)

            candidates.extend(extract_urls_from_text(value))

            for url in candidates:
                if not is_facebook_url(url):
                    continue

                row = build_source_row(
                    place_id=place_id,
                    place_name=place_name,
                    query="",
                    url=url,
                    title=place_name,
                    snippet="",
                    origin=f"master:{col}",
                )

                if row:
                    rows.append(row)

    return rows


# =====================
# SOURCE 2: GOOGLE SEARCH VIA APIFY
# =====================

def run_google_search(queries):
    actor_input = {
        "queries": "\n".join(queries),
        "maxPagesPerQuery": MAX_PAGES_PER_QUERY,
        "resultsPerPage": RESULTS_PER_PAGE,
        "countryCode": "vn",
        "languageCode": "vi",
        "mobileResults": False,
        "includeUnfilteredResults": False,
        "saveHtml": False,
    }

    run = client.actor(GOOGLE_ACTOR_ID).call(run_input=actor_input)
    dataset_id = run.get("defaultDatasetId")

    if not dataset_id:
        return []

    return list(client.dataset(dataset_id).iterate_items())


def extract_google_results(items):
    """
    Hỗ trợ 2 kiểu output phổ biến:
    1. Mỗi item có organicResults: [...]
    2. Mỗi item là một result riêng có url/title/description
    """
    results = []

    for item in items:
        query = (
            item.get("searchQuery")
            or item.get("query")
            or item.get("term")
            or ""
        )

        organic = item.get("organicResults")

        if isinstance(organic, list):
            for r in organic:
                results.append({
                    "query": query,
                    "url": r.get("url") or r.get("link") or "",
                    "title": r.get("title") or "",
                    "snippet": r.get("description") or r.get("snippet") or "",
                })
            continue

        url = item.get("url") or item.get("link") or ""
        title = item.get("title") or ""
        snippet = item.get("description") or item.get("snippet") or ""

        if url:
            results.append({
                "query": query,
                "url": url,
                "title": title,
                "snippet": snippet,
            })

    return results


def collect_sources_from_google(places):
    all_query_rows = []
    query_to_place = {}

    for _, place in places.iterrows():
        place_id = clean_text(place.get("place_id", ""))
        place_name = clean_text(place.get("title", ""))
        category = clean_text(place.get("category", ""))

        queries = build_queries(place_name, category)

        for q in queries:
            all_query_rows.append(q)
            query_to_place[q] = {
                "place_id": place_id,
                "place_name": place_name,
            }

    rows = []

    query_chunks = [
        all_query_rows[i:i + QUERY_CHUNK_SIZE]
        for i in range(0, len(all_query_rows), QUERY_CHUNK_SIZE)
    ]

    for chunk_index, query_chunk in enumerate(query_chunks, start=1):
        print(f"[GOOGLE] Chunk {chunk_index}/{len(query_chunks)} | queries={len(query_chunk)}")

        try:
            items = run_google_search(query_chunk)
            results = extract_google_results(items)

            for r in results:
                url = clean_text(r.get("url", ""))

                if not is_facebook_url(url):
                    continue

                query = clean_text(r.get("query", ""))

                # Nếu output không trả query, fallback match theo text
                place_meta = query_to_place.get(query)

                if not place_meta:
                    combined = normalize_text(
                        f"{r.get('title', '')} {r.get('snippet', '')} {url}"
                    )

                    best_place = None
                    best_score = 0

                    for _, p in places.iterrows():
                        name = clean_text(p.get("title", ""))
                        name_norm = normalize_text(name)

                        if name_norm and name_norm in combined:
                            best_place = p
                            best_score = 1
                            break

                    if best_place is None or best_score == 0:
                        continue

                    place_meta = {
                        "place_id": clean_text(best_place.get("place_id", "")),
                        "place_name": clean_text(best_place.get("title", "")),
                    }

                row = build_source_row(
                    place_id=place_meta["place_id"],
                    place_name=place_meta["place_name"],
                    query=query,
                    url=url,
                    title=r.get("title", ""),
                    snippet=r.get("snippet", ""),
                    origin="google_search",
                )

                if row:
                    rows.append(row)

            time.sleep(SLEEP_SECONDS)

        except Exception as e:
            print(f"[FAILED GOOGLE CHUNK] {chunk_index} | {e}")
            continue

    return rows


def select_places_slice(places, start_row=1, end_row=None, limit=None):
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


# =====================
# MAIN
# =====================

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--places-file", default=PLACES_FILE)
    parser.add_argument("--output-dir", default=OUTPUT_DIR)
    parser.add_argument("--start-row", type=int, default=1)
    parser.add_argument("--end-row", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--skip-google", action="store_true")
    parser.add_argument("--append", action="store_true")

    args = parser.parse_args()

    if args.end_row is not None and args.limit is not None:
        parser.error("Use either --end-row or --limit, not both.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / OUTPUT_FILE

    all_places = pd.read_csv(args.places_file)
    places = select_places_slice(
        all_places,
        start_row=args.start_row,
        end_row=args.end_row,
        limit=args.limit,
    )

    selected_start = places.index.min() + 1 if len(places) > 0 else 0
    selected_end = places.index.max() + 1 if len(places) > 0 else 0
    print(
        f"[INFO] Selected master rows {selected_start}-{selected_end} "
        f"({len(places)}/{len(all_places)} places)"
    )

    required_cols = {"place_id", "title", "category"}
    missing = required_cols - set(places.columns)

    if missing:
        raise ValueError(f"Missing required columns in places file: {missing}")

    rows = []

    print("[MASTER] Collecting Facebook links from master file...")
    rows.extend(collect_sources_from_master(places))

    if not args.skip_google:
        print("[GOOGLE] Searching Facebook sources via Apify Google Search...")
        rows.extend(collect_sources_from_google(places))

    sources = pd.DataFrame(rows)

    if len(sources) == 0:
        sources = pd.DataFrame(columns=[
            "source_id",
            "place_id",
            "place_name",
            "query",
            "source_url",
            "source_type",
            "source_title",
            "source_snippet",
            "source_origin",
            "source_score",
            "next_stage",
            "status",
            "scraped_at",
        ])
    else:
        sources = sources.sort_values(
            by=["source_score", "source_type"],
            ascending=[False, True]
        )
        sources = sources.drop_duplicates(subset=["source_id"], keep="first")

    if args.append and output_path.exists():
        old = pd.read_csv(output_path)
        sources = pd.concat([old, sources], ignore_index=True)
        sources = sources.sort_values(
            by=["source_score", "source_type"],
            ascending=[False, True]
        )
        sources = sources.drop_duplicates(subset=["source_id"], keep="first")

    sources.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("\nDone.")
    print(f"Saved: {output_path}")
    print(f"Total sources: {len(sources)}")

    if len(sources) > 0:
        print("\nBy source_type:")
        print(sources["source_type"].value_counts())

        print("\nBy next_stage:")
        print(sources["next_stage"].value_counts())

        print("\nBy place coverage:")
        covered_places = sources["place_id"].nunique()
        print(f"{covered_places}/{len(places)} places have at least 1 Facebook source")


if __name__ == "__main__":
    main()
