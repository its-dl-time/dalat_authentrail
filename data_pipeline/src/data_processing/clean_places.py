import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


# =========================
# 1. CONFIG - ĐIỀN PATH SAU
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PIPELINE_ROOT = Path(__file__).resolve().parents[2]
RAW_GOOGLE_PLACES_DIR = PIPELINE_ROOT / "data" / "raw" / "google_places"
PROCESSED_DATA_DIR = PIPELINE_ROOT / "data" / "processed"

INPUT_FILE_1 = RAW_GOOGLE_PLACES_DIR / "dataset_crawler-google-places_2026-05-11_03-51-59-108.json"
INPUT_FILE_2 = RAW_GOOGLE_PLACES_DIR / "dataset_crawler-google-places_2026-05-16_13-51-04-944.json"

OUTPUT_DIR = PROCESSED_DATA_DIR

MIN_REVIEWS = 100
TOP_N = 50


# =========================
# 2. BASIC UTILS
# =========================

def safe_str(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None or pd.isna(value) or value == "":
        return default

    try:
        if isinstance(value, str):
            value = value.replace(",", ".").strip()
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    if value is None or pd.isna(value) or value == "":
        return default

    try:
        if isinstance(value, str):
            value = value.replace(",", "").replace(".", "").strip()
        return int(float(value))
    except Exception:
        return default


def normalize_text(text: Any) -> str:
    text = safe_str(text).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def first_existing(row: pd.Series, keys: List[str], default: Any = "") -> Any:
    for key in keys:
        if key in row and not pd.isna(row[key]) and row[key] != "":
            return row[key]
    return default


# =========================
# 3. READ INPUT FILE
# =========================

def read_any_file(file_path: str) -> pd.DataFrame:
    """
    Hỗ trợ:
    - .json: list of dict hoặc dict
    - .jsonl
    - .csv
    - .tsv
    - .txt dạng tab-separated như file Apify export của bạn
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()

    if suffix == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return pd.json_normalize(data)

        if isinstance(data, dict):
            if "items" in data and isinstance(data["items"], list):
                return pd.json_normalize(data["items"])
            return pd.json_normalize([data])

        raise ValueError(f"Unsupported JSON structure: {file_path}")

    if suffix == ".jsonl":
        rows = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
        return pd.json_normalize(rows)

    if suffix in [".csv"]:
        return pd.read_csv(path)

    if suffix in [".tsv", ".txt"]:
        # File bạn đưa nhiều khả năng là TSV
        return pd.read_csv(path, sep="\t", low_memory=False)

    raise ValueError(f"Unsupported file type: {suffix}")


# =========================
# 4. STANDARDIZE PLACE ROWS
# =========================

def build_categories(row: pd.Series) -> str:
    category_values = []

    for col in row.index:
        if col.startswith("categories/"):
            value = safe_str(row[col])
            if value:
                category_values.append(value)

    # fallback
    category_name = safe_str(first_existing(row, ["categoryName", "category", "type"]))
    if category_name and category_name not in category_values:
        category_values.insert(0, category_name)

    return "|".join(dict.fromkeys(category_values))


def standardize_places(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, row in df.iterrows():
        place_id = first_existing(row, ["placeId", "place_id", "googlePlaceId", "cid", "fid"])
        cid = first_existing(row, ["cid"], "")

        title = first_existing(row, ["title", "name", "placeName"])
        category = first_existing(row, ["categoryName", "category", "type"])
        categories = build_categories(row)

        address = first_existing(row, ["address", "street", "subTitle", "formattedAddress"])
        city = first_existing(row, ["city"], "")
        state = first_existing(row, ["state"], "")
        country_code = first_existing(row, ["countryCode", "country_code"], "")

        lat = first_existing(row, ["location/lat", "location.lat", "lat", "latitude"])
        lng = first_existing(row, ["location/lng", "location.lng", "lng", "longitude"])

        google_maps_url = first_existing(row, ["url", "googleUrl", "searchPageUrl", "placeUrl"])
        website = first_existing(row, ["website"], "")
        phone = first_existing(row, ["phone", "phoneUnformatted"], "")

        total_score = first_existing(row, ["totalScore", "rating", "score"])
        reviews_count = first_existing(row, ["reviewsCount", "review_count", "user_ratings_total"])
        images_count = first_existing(row, ["imagesCount", "photosCount"], 0)
        price = first_existing(row, ["price", "priceLevel"], "")

        temporarily_closed = first_existing(row, ["temporarilyClosed"], False)
        permanently_closed = first_existing(row, ["permanentlyClosed"], False)

        search_string = first_existing(row, ["searchString", "query"], "")
        scraped_at = first_existing(row, ["scrapedAt", "scraped_at"], "")

        rows.append({
            "raw_place_id": safe_str(place_id),
            "cid": safe_str(cid),
            "title": safe_str(title),
            "category": safe_str(category),
            "categories": categories,
            "address": safe_str(address),
            "city": safe_str(city),
            "state": safe_str(state),
            "country_code": safe_str(country_code),
            "lat": safe_float(lat),
            "lng": safe_float(lng),
            "google_maps_url": safe_str(google_maps_url),
            "website": safe_str(website),
            "phone": safe_str(phone),
            "total_score": safe_float(total_score, 0),
            "reviews_count": safe_int(reviews_count, 0),
            "images_count": safe_int(images_count, 0),
            "price": safe_str(price),
            "temporarily_closed": temporarily_closed,
            "permanently_closed": permanently_closed,
            "search_string": safe_str(search_string),
            "scraped_at": safe_str(scraped_at),
        })

    out = pd.DataFrame(rows)

    # Loại dòng không có tên địa điểm
    out = out[out["title"].astype(str).str.strip() != ""]

    return out


# =========================
# 5. DEDUPE PLACES
# =========================

def make_dedupe_key(row: pd.Series) -> str:
    """
    Ưu tiên placeId.
    Nếu không có, dùng title + lat/lng.
    Nếu không có lat/lng, dùng title + address.
    """

    raw_place_id = safe_str(row.get("raw_place_id", ""))
    if raw_place_id:
        return f"placeid::{raw_place_id}"

    title = normalize_text(row.get("title", ""))
    lat = row.get("lat")
    lng = row.get("lng")

    if not pd.isna(lat) and not pd.isna(lng):
        return f"geo::{title}::{round(float(lat), 5)}::{round(float(lng), 5)}"

    address = normalize_text(row.get("address", ""))
    return f"text::{title}::{address}"


def dedupe_places(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["dedupe_key"] = df.apply(make_dedupe_key, axis=1)

    # Nếu trùng, giữ bản có nhiều review hơn
    df = df.sort_values(
        by=["reviews_count", "total_score", "images_count"],
        ascending=[False, False, False]
    )

    df = df.drop_duplicates(subset=["dedupe_key"], keep="first")

    return df


# =========================
# 6. SCORE & SELECT TOP 50
# =========================

def calculate_data_score(row: pd.Series) -> float:
    """
    Điểm chọn địa điểm.
    Trọng tâm vẫn là số review, vì mục tiêu là chọn nơi có đủ dữ liệu.
    """

    reviews_count = safe_int(row.get("reviews_count", 0))
    total_score = safe_float(row.get("total_score", 0), 0)
    images_count = safe_int(row.get("images_count", 0))

    # log để tránh địa điểm quá nổi tiếng nuốt hết điểm
    review_score = math.log1p(reviews_count)

    # rating 4.2 tốt hơn 3.5, nhưng không nên quá nặng
    rating_score = total_score if total_score else 0

    # ảnh nhiều thường đồng nghĩa địa điểm có nhiều dữ liệu trực quan
    image_score = math.log1p(images_count)

    data_score = (
        0.70 * review_score +
        0.20 * rating_score +
        0.10 * image_score
    )

    return round(data_score, 4)


def filter_bad_places(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # bỏ địa điểm đóng cửa vĩnh viễn
    if "permanently_closed" in df.columns:
        df = df[~df["permanently_closed"].astype(str).str.lower().isin(["true", "1", "yes"])]

    # bỏ địa điểm thiếu tọa độ
    df = df[~df["lat"].isna()]
    df = df[~df["lng"].isna()]

    # lọc số review tối thiểu
    df = df[df["reviews_count"] >= MIN_REVIEWS]

    return df


def select_top_places(df: pd.DataFrame) -> pd.DataFrame:
    df = filter_bad_places(df)

    df["data_score"] = df.apply(calculate_data_score, axis=1)

    df = df.sort_values(
        by=["data_score", "reviews_count", "total_score"],
        ascending=[False, False, False]
    )

    df = df.head(TOP_N).copy()

    # tạo place_id nội bộ ổn định
    df.insert(0, "place_id", [f"dalat_{i:03d}" for i in range(1, len(df) + 1)])

    core_columns = [
        "place_id",
        "raw_place_id",
        "cid",
        "title",
        "category",
        "categories",
        "address",
        "city",
        "state",
        "country_code",
        "lat",
        "lng",
        "google_maps_url",
        "website",
        "phone",
        "total_score",
        "reviews_count",
        "images_count",
        "price",
        "temporarily_closed",
        "permanently_closed",
        "search_string",
        "scraped_at",
        "data_score",
    ]

    existing_columns = [col for col in core_columns if col in df.columns]

    return df[existing_columns]


# =========================
# 7. OPTIONAL: EXTRACT REVIEWS LONG FORMAT
# =========================

def extract_reviews_long(df_raw: pd.DataFrame, places_selected: pd.DataFrame) -> pd.DataFrame:
    """
    Nếu file input có các cột kiểu:
    reviews/0/text
    reviews/0/rating
    reviews/0/reviewId
    ...
    thì chuyển thành bảng reviews_long.
    """

    selected_raw_ids = set(places_selected["raw_place_id"].astype(str))
    selected_cids = set(places_selected["cid"].astype(str))

    review_rows = []

    review_indices = set()

    for col in df_raw.columns:
        match = re.match(r"reviews/(\d+)/", col)
        if match:
            review_indices.add(int(match.group(1)))

    if not review_indices:
        return pd.DataFrame()

    for _, row in df_raw.iterrows():
        raw_place_id = safe_str(first_existing(row, ["placeId", "place_id", "googlePlaceId", "cid", "fid"]))
        cid = safe_str(first_existing(row, ["cid"], ""))
        title = safe_str(first_existing(row, ["title", "name", "placeName"]))

        if raw_place_id not in selected_raw_ids and cid not in selected_cids:
            continue

        for idx in sorted(review_indices):
            prefix = f"reviews/{idx}/"

            text = safe_str(row.get(prefix + "text", ""))
            text_translated = safe_str(row.get(prefix + "textTranslated", ""))

            if not text and not text_translated:
                continue

            review_id = safe_str(row.get(prefix + "reviewId", ""))
            reviewer_id = safe_str(row.get(prefix + "reviewerId", ""))
            reviewer_name = safe_str(row.get(prefix + "name", ""))

            review_rows.append({
                "raw_place_id": raw_place_id,
                "cid": cid,
                "place_title": title,
                "review_id": review_id,
                "reviewer_id": reviewer_id,
                "reviewer_name": reviewer_name,
                "rating": safe_float(row.get(prefix + "rating", row.get(prefix + "stars", None))),
                "stars": safe_float(row.get(prefix + "stars", None)),
                "text": text,
                "text_translated": text_translated,
                "original_language": safe_str(row.get(prefix + "originalLanguage", "")),
                "translated_language": safe_str(row.get(prefix + "translatedLanguage", "")),
                "published_at": safe_str(row.get(prefix + "publishedAtDate", "")),
                "publish_at_text": safe_str(row.get(prefix + "publishAt", "")),
                "likes_count": safe_int(row.get(prefix + "likesCount", 0)),
                "is_local_guide": row.get(prefix + "isLocalGuide", ""),
                "reviewer_number_of_reviews": safe_int(row.get(prefix + "reviewerNumberOfReviews", 0)),
                "review_url": safe_str(row.get(prefix + "reviewUrl", "")),
                "review_origin": safe_str(row.get(prefix + "reviewOrigin", "")),
            })

    return pd.DataFrame(review_rows)


# =========================
# 8. MAIN
# =========================

def main():
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Reading input files...")

    df1 = read_any_file(INPUT_FILE_1)
    df2 = read_any_file(INPUT_FILE_2)

    print(f"File 1 rows: {len(df1)}")
    print(f"File 2 rows: {len(df2)}")

    df_raw = pd.concat([df1, df2], ignore_index=True)

    print(f"Merged raw rows: {len(df_raw)}")

    print("Standardizing places...")
    places = standardize_places(df_raw)

    print(f"Standardized places: {len(places)}")

    print("Deduplicating places...")
    places = dedupe_places(places)

    print(f"Unique places after dedupe: {len(places)}")

    print("Selecting top places...")
    top_places = select_top_places(places)

    places_output = output_dir / "places_master_top50.csv"
    top_places.to_csv(places_output, index=False, encoding="utf-8-sig")

    print(f"Saved top places: {places_output}")
    print(f"Top places count: {len(top_places)}")

    print("Extracting embedded reviews if available...")
    reviews_long = extract_reviews_long(df_raw, top_places)

    if len(reviews_long) > 0:
        reviews_output = output_dir / "reviews_long.csv"
        reviews_long.to_csv(reviews_output, index=False, encoding="utf-8-sig")
        print(f"Saved reviews long file: {reviews_output}")
        print(f"Extracted reviews: {len(reviews_long)}")
    else:
        print("No embedded reviews found.")

    print("Done.")


if __name__ == "__main__":
    main()
