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

ACTOR_ID = "compass/google-maps-reviews-scraper"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PLACES_FILE = PROJECT_ROOT / "data" / "processed" / "places_master_top50.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs" / "google_maps"
OUTPUT_FILE = "google_maps_reviews_output.csv"

REVIEWS_PER_PLACE = 20
BATCH_SIZE = 5
SLEEP_SECONDS = 2

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


def safe_float(value, default=None):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def get_first(item, keys, default=""):
    for key in keys:
        value = item.get(key)
        if value not in [None, ""]:
            return value
    return default


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


# =====================
# FIELD EXTRACTION
# =====================

def extract_review_id(item):
    return clean_text(get_first(item, [
        "reviewId",
        "review_id",
        "id",
        "cid",
        "reviewUrl",
        "url",
    ]))


def extract_review_text(item):
    return clean_text(get_first(item, [
        "text",
        "reviewText",
        "review",
        "comment",
        "description",
        "textTranslated",
    ]))


def extract_rating(item):
    return safe_float(get_first(item, [
        "stars",
        "rating",
        "reviewRating",
        "score",
    ]))


def extract_published_at(item):
    return clean_text(get_first(item, [
        "publishedAtDate",
        "publishedAt",
        "publishAt",
        "date",
        "createdAt",
        "time",
    ]))


def extract_review_url(item):
    return clean_text(get_first(item, [
        "reviewUrl",
        "url",
        "link",
    ]))


def extract_reviewer_name(item):
    return clean_text(get_first(item, [
        "name",
        "reviewerName",
        "authorName",
        "userName",
    ]))


def extract_reviewer_id(item):
    return clean_text(get_first(item, [
        "reviewerId",
        "authorId",
        "userId",
        "reviewerUrl",
    ]))


def extract_reviewer_url(item):
    return clean_text(get_first(item, [
        "reviewerUrl",
        "authorUrl",
        "userUrl",
        "profileUrl",
    ]))


def extract_reviewer_number_of_reviews(item):
    return safe_int(get_first(item, [
        "reviewerNumberOfReviews",
        "numberOfReviews",
        "reviewsCount",
    ], 0))


def extract_is_local_guide(item):
    value = get_first(item, [
        "isLocalGuide",
        "localGuide",
        "reviewerIsLocalGuide",
    ], "")

    if isinstance(value, bool):
        return value

    value = clean_text(value).lower()
    return value in ["true", "1", "yes"]


def extract_likes_count(item):
    return safe_int(get_first(item, [
        "likesCount",
        "helpfulCount",
        "likes",
    ], 0))


def extract_owner_response_text(item):
    return clean_text(get_first(item, [
        "responseFromOwnerText",
        "ownerResponse",
        "ownerResponseText",
        "replyText",
    ]))


def extract_owner_response_date(item):
    return clean_text(get_first(item, [
        "responseFromOwnerDate",
        "ownerResponseDate",
        "replyDate",
    ]))


# =====================
# APIFY
# =====================

def build_actor_input(place_urls):
    """
    Actor compass/google-maps-reviews-scraper thường dùng startUrls.
    Nếu actor báo lỗi input field, gửi traceback lại, ta sửa đúng schema.
    """
    return {
        "startUrls": [{"url": url} for url in place_urls],
        "maxReviews": REVIEWS_PER_PLACE,
        "sort": "newest",
        "language": "vi",
    }


def run_reviews_actor(place_urls):
    actor_input = build_actor_input(place_urls)

    run = client.actor(ACTOR_ID).call(run_input=actor_input)
    dataset_id = run.get("defaultDatasetId")

    if not dataset_id:
        return []

    return list(client.dataset(dataset_id).iterate_items())


# =====================
# MAIN PIPELINE
# =====================

def prepare_places(places, limit=None, start_row=1):
    df = places.copy()

    required = {"place_id", "title", "google_maps_url"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in master file: {missing}")

    df["google_maps_url"] = df["google_maps_url"].apply(clean_text)
    df = df[df["google_maps_url"] != ""]

    if start_row < 1:
        raise ValueError("--start-row must be >= 1")

    start_index = start_row - 1
    df = df.iloc[start_index:]

    if limit:
        df = df.head(limit)

    return df


def crawl_google_reviews(places, append=False):
    rows = []

    batches = [
        places.iloc[i:i + BATCH_SIZE]
        for i in range(0, len(places), BATCH_SIZE)
    ]

    for batch_index, batch in enumerate(batches, start=1):
        urls = batch["google_maps_url"].tolist()

        print(f"[GOOGLE MAPS] Batch {batch_index}/{len(batches)} | places={len(urls)}")

        place_map = {
            clean_text(row["google_maps_url"]): row.to_dict()
            for _, row in batch.iterrows()
        }

        try:
            items = run_reviews_actor(urls)

            for item in items:
                # Actor thường trả place URL hoặc input URL, nhưng không chắc tên field.
                item_place_url = clean_text(get_first(item, [
                    "placeUrl",
                    "googleMapsUrl",
                    "googleUrl",
                    "url",
                    "inputUrl",
                    "searchPageUrl",
                ]))

                place = None

                if item_place_url in place_map:
                    place = place_map[item_place_url]
                elif len(place_map) == 1:
                    place = list(place_map.values())[0]
                else:
                    # fallback: nếu item không trả URL input, match bằng title/place name
                    item_place_name = normalize_text(get_first(item, [
                        "title",
                        "placeName",
                        "name",
                    ]))

                    for _, p in batch.iterrows():
                        if normalize_text(p.get("title", "")) in item_place_name:
                            place = p.to_dict()
                            break

                if place is None:
                    continue

                place_id = clean_text(place.get("place_id", ""))
                place_name = clean_text(place.get("title", ""))
                place_category = clean_text(place.get("category", ""))
                google_maps_url = clean_text(place.get("google_maps_url", ""))

                review_id = extract_review_id(item)
                review_text = extract_review_text(item)
                rating = extract_rating(item)
                published_at = extract_published_at(item)

                fallback_id = make_id(
                    place_id,
                    extract_reviewer_name(item),
                    rating,
                    review_text,
                    published_at,
                )

                global_id = make_id("google_maps", review_id or fallback_id)

                rows.append({
                    "id": global_id,
                    "platform": "google_maps",
                    "place_id": place_id,
                    "place_name": place_name,
                    "place_category": place_category,
                    "google_maps_url": google_maps_url,
                    "review_id": review_id,
                    "review_url": extract_review_url(item),
                    "review_text": review_text,
                    "rating": rating,
                    "published_at": published_at,
                    "reviewer_name": extract_reviewer_name(item),
                    "reviewer_id": extract_reviewer_id(item),
                    "reviewer_url": extract_reviewer_url(item),
                    "reviewer_number_of_reviews": extract_reviewer_number_of_reviews(item),
                    "is_local_guide": extract_is_local_guide(item),
                    "likes_count": extract_likes_count(item),
                    "owner_response_text": extract_owner_response_text(item),
                    "owner_response_date": extract_owner_response_date(item),
                    "scraped_at": datetime.now().isoformat(),
                })

            time.sleep(SLEEP_SECONDS)

        except Exception as e:
            print(f"[FAILED GOOGLE MAPS BATCH] {batch_index} | {e}")
            continue

    df = pd.DataFrame(rows)

    if len(df) > 0:
        df = df.drop_duplicates(subset=["id"], keep="last")

    output_path = str(Path(OUTPUT_DIR) / OUTPUT_FILE)

    saved = save_output(
        df,
        output_path,
        append=append,
        dedupe_subset=["id"],
    )

    print("\nDone.")
    print(f"Saved: {output_path}")
    print(f"Reviews this run: {len(df)}")
    print(f"Reviews total file: {len(saved)}")

    if len(saved) > 0:
        print("\nCoverage:")
        print(f"Places with reviews: {saved['place_id'].nunique()}")
        print("\nTop places by review count:")
        print(saved["place_name"].value_counts().head(10))


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--places-file", default=PLACES_FILE)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--start-row", type=int, default=1)
    parser.add_argument("--append", action="store_true")

    args = parser.parse_args()

    places_file = Path(args.places_file)

    if not places_file.exists():
        raise FileNotFoundError(f"Missing places file: {places_file}")

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    places = pd.read_csv(places_file)
    selected_places = prepare_places(
        places=places,
        limit=args.limit,
        start_row=args.start_row,
    )

    print(f"Selected places: {len(selected_places)}")

    if len(selected_places) == 0:
        print("No places with google_maps_url found.")
        return

    crawl_google_reviews(
        places=selected_places,
        append=args.append,
    )


if __name__ == "__main__":
    main()
