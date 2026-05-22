from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from .common.apify import call_actor_items
    from .common.config import INTERIM_DIR, MASTER_PLACES_FILE, OUTPUTS_DIR, RAW_DIR, make_run_id
    from .common.ids import make_id
    from .common.io import append_jsonl, read_jsonl_dir, read_master_places, save_csv
    from .common.text import clean_text, get_first, safe_float, safe_int
except ImportError:
    from common.apify import call_actor_items
    from common.config import INTERIM_DIR, MASTER_PLACES_FILE, OUTPUTS_DIR, RAW_DIR, make_run_id
    from common.ids import make_id
    from common.io import append_jsonl, read_jsonl_dir, read_master_places, save_csv
    from common.text import clean_text, get_first, safe_float, safe_int


ACTOR_ID = "compass/google-maps-reviews-scraper"

RAW_REVIEWS_DIR = RAW_DIR / "google_maps" / "reviews"
INTERIM_FILE = INTERIM_DIR / "google_maps_reviews_mapped.csv"
OUTPUT_FILE = OUTPUTS_DIR / "google_maps" / "google_maps_reviews_output.csv"

DEFAULT_REVIEWS_PER_PLACE = 200
DEFAULT_BATCH_SIZE = 5
DEFAULT_SLEEP_SECONDS = 2

OUTPUT_COLUMNS = [
    "id",
    "platform",
    "place_id",
    "place_name",
    "place_category",
    "google_maps_url",
    "review_id",
    "review_url",
    "review_text",
    "rating",
    "published_at",
    "reviewer_name",
    "reviewer_id",
    "reviewer_url",
    "reviewer_number_of_reviews",
    "is_local_guide",
    "likes_count",
    "owner_response_text",
    "owner_response_date",
    "scraped_at",
]


def select_places(places: pd.DataFrame, start_row: int = 1, end_row: int | None = None, limit: int | None = None) -> pd.DataFrame:
    if start_row < 1:
        raise ValueError("--start-row must be >= 1")
    if end_row is not None and limit is not None:
        raise ValueError("Use either --end-row or --limit, not both.")
    if end_row is not None and end_row < start_row:
        raise ValueError("--end-row must be >= --start-row")

    required = {"place_id", "title", "google_maps_url"}
    missing = required - set(places.columns)
    if missing:
        raise ValueError(f"Missing required columns in master file: {missing}")

    places = places.copy()
    places["google_maps_url"] = places["google_maps_url"].apply(clean_text)
    places = places[places["google_maps_url"] != ""]

    start_index = start_row - 1
    if start_index >= len(places):
        raise ValueError(f"--start-row={start_row} is outside selected master range.")

    if end_row is not None:
        return places.iloc[start_index:min(end_row, len(places))].copy()
    if limit is not None:
        return places.iloc[start_index:start_index + limit].copy()
    return places.iloc[start_index:start_index + 50].copy()


def build_actor_input(place_urls: list[str], reviews_per_place: int) -> dict:
    return {
        "startUrls": [{"url": url} for url in place_urls],
        "maxReviews": reviews_per_place,
        "sort": "newest",
        "language": "vi",
    }


def crawl(args: argparse.Namespace) -> None:
    places = select_places(
        read_master_places(args.places_file),
        start_row=args.start_row,
        end_row=args.end_row,
        limit=args.limit,
    )
    run_id = args.run_id or make_run_id("google_maps_reviews")
    raw_path = RAW_REVIEWS_DIR / f"{run_id}.jsonl"
    batches = [
        places.iloc[i:i + args.batch_size]
        for i in range(0, len(places), args.batch_size)
    ]

    print(f"[GOOGLE MAPS] Selected places: {len(places)}")
    print(f"[GOOGLE MAPS] Raw output: {raw_path}")

    total_saved = 0
    for batch_index, batch in enumerate(batches, start=1):
        urls = batch["google_maps_url"].tolist()
        actor_input = build_actor_input(urls, args.reviews_per_place)
        print(f"[GOOGLE MAPS] Batch {batch_index}/{len(batches)} | places={len(urls)}")

        if args.dry_run:
            print(f"[DRY RUN] actor={ACTOR_ID} input_urls={len(urls)} maxReviews={args.reviews_per_place}")
            continue

        try:
            items, run = call_actor_items(ACTOR_ID, actor_input)
            rows = [{
                "run_id": run_id,
                "platform": "google_maps",
                "actor_id": ACTOR_ID,
                "actor_run_id": run.get("id", ""),
                "default_dataset_id": run.get("defaultDatasetId", ""),
                "input_urls": urls,
                "raw_item": item,
                "scraped_at": datetime.now().isoformat(),
            } for item in items]
            total_saved += append_jsonl(rows, raw_path)
            time.sleep(args.sleep_seconds)
        except Exception as exc:
            print(f"[FAILED GOOGLE MAPS BATCH] {batch_index} | {exc}")

    print(f"[GOOGLE MAPS] Raw rows saved: {total_saved}")
    if args.process and not args.dry_run:
        process(args)


def extract_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return clean_text(value).lower() in {"true", "1", "yes", "y"}


def extract_place_url(item: dict) -> str:
    return clean_text(get_first(item, ["placeUrl", "googleMapsUrl", "googleUrl", "url", "inputUrl", "searchPageUrl"]))


def map_raw_item(raw_row: dict, place_map: dict[str, dict], fallback_places: list[dict]) -> dict | None:
    item = raw_row.get("raw_item") or {}
    item_place_url = extract_place_url(item)
    place = place_map.get(item_place_url)

    if place is None and len(fallback_places) == 1:
        place = fallback_places[0]

    if place is None:
        item_place_name = clean_text(get_first(item, ["title", "placeName", "name"])).lower()
        for candidate in fallback_places:
            candidate_name = clean_text(candidate.get("title", "")).lower()
            if candidate_name and candidate_name in item_place_name:
                place = candidate
                break

    if place is None:
        return None

    review_id = clean_text(get_first(item, ["reviewId", "review_id", "id", "cid", "reviewUrl", "url"]))
    review_text = clean_text(get_first(item, ["text", "reviewText", "review", "comment", "description", "textTranslated"]))
    rating = safe_float(get_first(item, ["stars", "rating", "reviewRating", "score"]))
    published_at = clean_text(get_first(item, ["publishedAtDate", "publishedAt", "publishAt", "date", "createdAt", "time"]))
    fallback_id = make_id(place.get("place_id", ""), get_first(item, ["name", "reviewerName", "authorName"]), rating, review_text, published_at)

    return {
        "id": make_id("google_maps", review_id or fallback_id),
        "platform": "google_maps",
        "place_id": clean_text(place.get("place_id", "")),
        "place_name": clean_text(place.get("title", "")),
        "place_category": clean_text(place.get("category", "")),
        "google_maps_url": clean_text(place.get("google_maps_url", "")),
        "review_id": review_id,
        "review_url": clean_text(get_first(item, ["reviewUrl", "url", "link"])),
        "review_text": review_text,
        "rating": rating,
        "published_at": published_at,
        "reviewer_name": clean_text(get_first(item, ["name", "reviewerName", "authorName", "userName"])),
        "reviewer_id": clean_text(get_first(item, ["reviewerId", "authorId", "userId", "reviewerUrl"])),
        "reviewer_url": clean_text(get_first(item, ["reviewerUrl", "authorUrl", "userUrl", "profileUrl"])),
        "reviewer_number_of_reviews": safe_int(get_first(item, ["reviewerNumberOfReviews", "numberOfReviews", "reviewsCount"], 0)),
        "is_local_guide": extract_bool(get_first(item, ["isLocalGuide", "localGuide", "reviewerIsLocalGuide"], "")),
        "likes_count": safe_int(get_first(item, ["likesCount", "helpfulCount", "likes"], 0)),
        "owner_response_text": clean_text(get_first(item, ["responseFromOwnerText", "ownerResponse", "ownerResponseText", "replyText"])),
        "owner_response_date": clean_text(get_first(item, ["responseFromOwnerDate", "ownerResponseDate", "replyDate"])),
        "scraped_at": raw_row.get("scraped_at") or datetime.now().isoformat(),
    }


def process(args: argparse.Namespace) -> None:
    raw_rows = read_jsonl_dir(args.raw_dir)
    if not raw_rows:
        if OUTPUT_FILE.exists():
            print(f"[GOOGLE MAPS] No raw rows found in {args.raw_dir}. Existing output kept: {OUTPUT_FILE}")
            return
        raise FileNotFoundError(f"No raw rows found in {args.raw_dir}")

    places = read_master_places(args.places_file)
    place_records = places.to_dict(orient="records")
    place_map = {
        clean_text(place.get("google_maps_url", "")): place
        for place in place_records
        if clean_text(place.get("google_maps_url", ""))
    }

    rows = []
    for raw_row in raw_rows:
        row = map_raw_item(raw_row, place_map, place_records)
        if row:
            rows.append(row)

    df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if len(df) > 0:
        df = df.drop_duplicates(subset=["id"], keep="last")

    save_csv(df, INTERIM_FILE, append=False, dedupe_subset=["id"])
    saved = save_csv(df, OUTPUT_FILE, append=args.append, dedupe_subset=["id"])

    print("[GOOGLE MAPS] Process complete.")
    print(f"Interim: {INTERIM_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Rows this process: {len(df)}")
    print(f"Rows output total: {len(saved)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Raw-first Google Maps reviews pipeline.")
    sub = parser.add_subparsers(dest="command")

    crawl_parser = sub.add_parser("crawl", help="Crawl raw Google Maps reviews and save JSONL.")
    crawl_parser.add_argument("--places-file", type=Path, default=MASTER_PLACES_FILE)
    crawl_parser.add_argument("--start-row", type=int, default=1)
    crawl_parser.add_argument("--end-row", type=int, default=None)
    crawl_parser.add_argument("--limit", type=int, default=50)
    crawl_parser.add_argument("--reviews-per-place", type=int, default=DEFAULT_REVIEWS_PER_PLACE)
    crawl_parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    crawl_parser.add_argument("--sleep-seconds", type=int, default=DEFAULT_SLEEP_SECONDS)
    crawl_parser.add_argument("--run-id", default="")
    crawl_parser.add_argument("--dry-run", action="store_true")
    crawl_parser.add_argument("--process", action="store_true", help="Process raw rows after crawl.")
    crawl_parser.add_argument("--append", action="store_true", help="Append to platform-clean output during --process.")
    crawl_parser.set_defaults(func=crawl, raw_dir=RAW_REVIEWS_DIR)

    process_parser = sub.add_parser("process", help="Process saved raw Google Maps reviews.")
    process_parser.add_argument("--places-file", type=Path, default=MASTER_PLACES_FILE)
    process_parser.add_argument("--raw-dir", type=Path, default=RAW_REVIEWS_DIR)
    process_parser.add_argument("--append", action="store_true")
    process_parser.set_defaults(func=process)

    return parser


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] not in {"crawl", "process", "-h", "--help"}:
        sys.argv.insert(1, "crawl")

    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
