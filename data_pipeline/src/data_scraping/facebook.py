from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from .common.config import INTERIM_DIR, MASTER_PLACES_FILE, OUTPUTS_DIR, RAW_DIR, make_run_id
    from .common.ids import make_id
    from .common.io import append_jsonl, read_jsonl_dir, read_master_places, save_csv
    from .common.text import clean_text, normalize_text, safe_int
except ImportError:
    from common.config import INTERIM_DIR, MASTER_PLACES_FILE, OUTPUTS_DIR, RAW_DIR, make_run_id
    from common.ids import make_id
    from common.io import append_jsonl, read_jsonl_dir, read_master_places, save_csv
    from common.text import clean_text, normalize_text, safe_int


SCRIPT_DIR = Path(__file__).resolve().parent
RAW_SOURCES_DIR = RAW_DIR / "facebook" / "sources"
RAW_POSTS_DIR = RAW_DIR / "facebook" / "posts"
RAW_COMMENTS_DIR = RAW_DIR / "facebook" / "comments"
FACEBOOK_OUTPUT_DIR = OUTPUTS_DIR / "facebook"

SOURCES_FILE = FACEBOOK_OUTPUT_DIR / "facebook_sources.csv"
POST_SEEDS_FILE = FACEBOOK_OUTPUT_DIR / "facebook_post_seeds.csv"
POST_REJECTIONS_FILE = FACEBOOK_OUTPUT_DIR / "facebook_post_rejections.csv"
COMMENTS_FILE = FACEBOOK_OUTPUT_DIR / "facebook_comments_output.csv"

SOURCE_CANDIDATES_FILE = INTERIM_DIR / "facebook_source_candidates.csv"
POST_CANDIDATES_FILE = INTERIM_DIR / "facebook_post_candidates.csv"
COMMENT_CANDIDATES_FILE = INTERIM_DIR / "facebook_comment_candidates.csv"


def read_jsonl_file(path: Path | str) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def latest_jsonl_file(directory: Path | str) -> Path | None:
    directory = Path(directory)
    files = sorted(directory.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def read_raw_inputs(raw_dir: Path | str, raw_file: Path | str = "", latest: bool = False) -> tuple[list[dict], list[Path]]:
    if raw_file:
        path = Path(raw_file)
        return read_jsonl_file(path), [path]
    if latest:
        path = latest_jsonl_file(raw_dir)
        if path is None:
            return [], []
        return read_jsonl_file(path), [path]
    directory = Path(raw_dir)
    files = sorted(directory.glob("*.jsonl")) if directory.exists() else []
    rows: list[dict] = []
    for path in files:
        rows.extend(read_jsonl_file(path))
    return rows, files


def print_raw_inputs(label: str, rows: list[dict], input_files: list[Path]) -> None:
    print(f"[{label}] Processing raw inputs:")
    for path in input_files:
        print(f"  - {path}")
    print(f"[{label}] Raw rows: {len(rows)}")


def print_place_counts(label: str, rows) -> None:
    if rows is None or len(rows) == 0:
        print(f"[{label}] Places: none")
        return
    if isinstance(rows, pd.DataFrame):
        if "place_id" not in rows.columns:
            return
        values = rows["place_id"].astype(str).tolist()
    else:
        values = [str(row.get("place_id", "")) for row in rows]
    counts = Counter(value for value in values if value)
    if not counts:
        print(f"[{label}] Places: none")
        return
    summary = ", ".join(f"{place_id}:{count}" for place_id, count in sorted(counts.items()))
    print(f"[{label}] Places: {summary}")


def load_stage(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_place_ids(value: str) -> list[str]:
    return [clean_text(x) for x in str(value or "").split(",") if clean_text(x)]


def format_place_ids(place_ids: list[str]) -> str:
    return ",".join(place_ids)


def limit_rows_per_place(df: pd.DataFrame, limit: int | None) -> pd.DataFrame:
    if limit is None or limit <= 0 or len(df) == 0 or "place_id" not in df.columns:
        return df
    return df.groupby("place_id", group_keys=False).head(limit).reset_index(drop=True)


def coerce_query_text(value) -> str:
    if isinstance(value, dict):
        return clean_text(value.get("term") or value.get("query") or value.get("url") or "")
    return clean_text(value)


def place_from_raw_query(raw_row: dict, query: str) -> dict | None:
    query = coerce_query_text(query)
    for item in raw_row.get("query_chunk") or []:
        item_query = coerce_query_text(item.get("query"))
        if item_query and item_query == query:
            return {
                "place_id": clean_text(item.get("place_id", "")),
                "place_name": clean_text(item.get("place_name", "")),
            }
    if len(raw_row.get("query_chunk") or []) == 1:
        item = raw_row["query_chunk"][0]
        return {
            "place_id": clean_text(item.get("place_id", "")),
            "place_name": clean_text(item.get("place_name", "")),
        }
    return None


def select_places(args: argparse.Namespace, fb_sources_module) -> pd.DataFrame:
    places = read_master_places(args.places_file)
    place_ids = parse_place_ids(getattr(args, "place_ids", ""))
    if place_ids:
        selected = places[places["place_id"].astype(str).isin(place_ids)].copy()
        missing = [place_id for place_id in place_ids if place_id not in set(selected["place_id"].astype(str))]
        if missing:
            print(f"[FACEBOOK] Missing place_ids in master file: {', '.join(missing)}")
        return selected
    return fb_sources_module.select_places_slice(
        places,
        start_row=args.start_row,
        end_row=args.end_row,
        limit=args.limit,
    )


def crawl_sources(args: argparse.Namespace) -> None:
    fb1 = load_stage("01_facebook_gg.py", "facebook_sources_stage")
    places = select_places(args, fb1)
    run_id = args.run_id or make_run_id("facebook_sources")
    raw_path = RAW_SOURCES_DIR / f"{run_id}.jsonl"

    print(f"[FACEBOOK SOURCES] Selected places: {len(places)}")
    print(f"[FACEBOOK SOURCES] Raw output: {raw_path}")

    rows = []
    for source_row in fb1.collect_sources_from_master(places):
        rows.append({
            "run_id": run_id,
            "platform": "facebook",
            "stage": "sources",
            "origin": "master",
            "source_row": source_row,
            "scraped_at": datetime.now().isoformat(),
        })

    if not args.skip_google:
        all_queries = []
        for _, place in places.iterrows():
            place_id = clean_text(place.get("place_id", ""))
            place_name = clean_text(place.get("title", ""))
            category = clean_text(place.get("category", ""))
            for query in fb1.build_queries(place_name, category):
                all_queries.append({
                    "query": query,
                    "place_id": place_id,
                    "place_name": place_name,
                })

        query_chunks = [
            all_queries[i:i + args.query_chunk_size]
            for i in range(0, len(all_queries), args.query_chunk_size)
        ]

        for chunk_index, query_chunk in enumerate(query_chunks, start=1):
            queries = [row["query"] for row in query_chunk]
            print(f"[FACEBOOK SOURCES] Google chunk {chunk_index}/{len(query_chunks)} | queries={len(queries)}")
            if args.dry_run:
                continue
            try:
                items = fb1.run_google_search(queries)
                for item in items:
                    rows.append({
                        "run_id": run_id,
                        "platform": "facebook",
                        "stage": "sources",
                        "origin": "google_search",
                        "query_chunk": query_chunk,
                        "raw_item": item,
                        "scraped_at": datetime.now().isoformat(),
                    })
                time.sleep(args.sleep_seconds)
            except Exception as exc:
                print(f"[FAILED FACEBOOK SOURCE CHUNK] {chunk_index} | {exc}")

    if not args.dry_run:
        saved = append_jsonl(rows, raw_path)
        print(f"[FACEBOOK SOURCES] Raw rows saved: {saved}")
        print("[FACEBOOK SOURCES] Next process command:")
        print(f"python data_pipeline\\src\\data_scraping\\facebook.py process-sources --raw-file \"{raw_path}\"")
    if args.process and not args.dry_run:
        args.raw_file = raw_path
        args.latest = False
        process_sources(args)


def selected_place_ids(args: argparse.Namespace) -> list[str]:
    place_ids = parse_place_ids(getattr(args, "place_ids", ""))
    if place_ids:
        return place_ids
    fb1 = load_stage("01_facebook_gg.py", "facebook_sources_stage")
    places = select_places(args, fb1)
    return [clean_text(place_id) for place_id in places["place_id"].tolist() if clean_text(place_id)]


def run_all(args: argparse.Namespace) -> None:
    place_ids = selected_place_ids(args)
    place_ids_arg = format_place_ids(place_ids)

    print("=" * 72)
    print("Facebook crawl: source -> post -> comment")
    print("=" * 72)
    print(f"Places selected: {len(place_ids)}")
    print(f"Place IDs: {place_ids_arg or '(none)'}")
    print(f"Append mode: {'on' if args.append else 'off'}")
    if args.dry_run:
        print("Dry run: no Apify calls and no files will be written.")

    if not place_ids:
        print("[FACEBOOK] No places selected. Stop.")
        return

    source_args = argparse.Namespace(
        places_file=args.places_file,
        start_row=args.start_row,
        end_row=args.end_row,
        limit=args.limit,
        place_ids=place_ids_arg,
        skip_google=args.skip_google,
        query_chunk_size=args.query_chunk_size,
        sleep_seconds=args.sleep_seconds,
        run_id=args.run_id,
        dry_run=args.dry_run,
        process=True,
        append=args.append,
        raw_dir=RAW_SOURCES_DIR,
    )
    crawl_sources(source_args)

    if args.skip_posts:
        print("[FACEBOOK] Skip post stage.")
    else:
        post_args = argparse.Namespace(
            sources_file=SOURCES_FILE,
            limit_sources=args.limit_sources,
            limit_sources_per_place=args.limit_sources_per_place,
            place_ids=place_ids_arg,
            include_groups=args.include_groups,
            source_batch_size=args.source_batch_size,
            sleep_seconds=args.sleep_seconds,
            run_id="",
            dry_run=args.dry_run,
            process=True,
            append=args.append,
            raw_dir=RAW_POSTS_DIR,
        )
        crawl_posts(post_args)

    if args.skip_comments:
        print("[FACEBOOK] Skip comment stage.")
    else:
        comment_args = argparse.Namespace(
            limit_posts=args.limit_posts,
            limit_posts_per_place=args.limit_posts_per_place,
            place_ids=place_ids_arg,
            no_direct_sources=args.no_direct_sources,
            batch_size=args.comments_batch_size,
            comments_limit=args.comments_limit,
            sleep_seconds=args.sleep_seconds,
            run_id="",
            dry_run=args.dry_run,
            process=True,
            append=args.append,
            raw_dir=RAW_COMMENTS_DIR,
        )
        crawl_comments(comment_args)

    print("=" * 72)
    print("Facebook crawl completed.")
    print(f"Sources: {SOURCES_FILE}")
    print(f"Post seeds: {POST_SEEDS_FILE}")
    print(f"Comments: {COMMENTS_FILE}")
    print("=" * 72)


def process_sources(args: argparse.Namespace) -> None:
    fb1 = load_stage("01_facebook_gg.py", "facebook_sources_stage")
    raw_rows, input_files = read_raw_inputs(args.raw_dir, args.raw_file, args.latest)
    if not raw_rows:
        if SOURCES_FILE.exists():
            print(f"[FACEBOOK SOURCES] No raw rows found. Existing output kept: {SOURCES_FILE}")
            return
        raise FileNotFoundError(f"No raw rows found in {args.raw_dir}")

    print_raw_inputs("FACEBOOK SOURCES", raw_rows, input_files)

    places = read_master_places(args.places_file)
    query_to_place = {}
    for _, place in places.iterrows():
        place_name = clean_text(place.get("title", ""))
        category = clean_text(place.get("category", ""))
        for query in fb1.build_queries(place_name, category):
            query_to_place[query] = {
                "place_id": clean_text(place.get("place_id", "")),
                "place_name": place_name,
            }

    rows = []
    for raw_row in raw_rows:
        if raw_row.get("origin") == "master":
            source_row = raw_row.get("source_row") or {}
            if source_row:
                rows.append(source_row)
            continue

        for result in fb1.extract_google_results([raw_row.get("raw_item") or {}]):
            url = clean_text(result.get("url", ""))
            if not fb1.is_facebook_url(url):
                continue
            query = coerce_query_text(result.get("query", ""))
            place_meta = place_from_raw_query(raw_row, query) or query_to_place.get(query)

            if not place_meta:
                combined = normalize_text(f"{result.get('title', '')} {result.get('snippet', '')} {url}")
                for _, place in places.iterrows():
                    place_name = clean_text(place.get("title", ""))
                    if place_name and normalize_text(place_name) in combined:
                        place_meta = {
                            "place_id": clean_text(place.get("place_id", "")),
                            "place_name": place_name,
                        }
                        break

            if not place_meta:
                continue

            source = fb1.build_source_row(
                place_id=place_meta["place_id"],
                place_name=place_meta["place_name"],
                query=query,
                url=url,
                title=result.get("title", ""),
                snippet=result.get("snippet", ""),
                origin="google_search",
            )
            if source:
                rows.append(source)

    columns = [
        "source_id", "place_id", "place_name", "query", "source_url", "source_type",
        "source_title", "source_snippet", "source_origin", "source_score", "next_stage",
        "status", "scraped_at",
    ]
    sources = pd.DataFrame(rows, columns=columns)
    if len(sources) > 0:
        sources = sources.sort_values(by=["source_score", "source_type"], ascending=[False, True])
        sources = sources.drop_duplicates(subset=["source_id"], keep="first")

    save_csv(sources, SOURCE_CANDIDATES_FILE, append=False, dedupe_subset=["source_id"])
    saved = save_csv(sources, SOURCES_FILE, append=args.append, dedupe_subset=["source_id"])
    print(f"[FACEBOOK SOURCES] Output: {SOURCES_FILE}")
    print(f"[FACEBOOK SOURCES] Rows total: {len(saved)}")
    print_place_counts("FACEBOOK SOURCES", saved)


def crawl_posts(args: argparse.Namespace) -> None:
    fb2 = load_stage("02_facebook_posts.py", "facebook_posts_stage")
    sources = pd.read_csv(args.sources_file, dtype=str, keep_default_na=False)
    selected = fb2.prepare_sources(
        sources,
        limit=args.limit_sources,
        include_groups=args.include_groups,
        place_ids=parse_place_ids(args.place_ids),
    )
    selected = limit_rows_per_place(selected, args.limit_sources_per_place)
    run_id = args.run_id or make_run_id("facebook_posts")
    raw_path = RAW_POSTS_DIR / f"{run_id}.jsonl"

    print(f"[FACEBOOK POSTS] Selected sources: {len(selected)}")
    print_place_counts("FACEBOOK POSTS", selected)
    rows = []
    batches = [selected.iloc[i:i + args.source_batch_size] for i in range(0, len(selected), args.source_batch_size)]
    for batch_index, batch in enumerate(batches, start=1):
        urls = batch["source_url"].tolist()
        print(f"[FACEBOOK POSTS] Batch {batch_index}/{len(batches)} | sources={len(urls)}")
        if args.dry_run:
            continue
        try:
            items = fb2.run_facebook_posts_actor(urls)
            source_records = batch.to_dict(orient="records")
            for item in items:
                rows.append({
                    "run_id": run_id,
                    "platform": "facebook",
                    "stage": "posts",
                    "sources": source_records,
                    "raw_item": item,
                    "scraped_at": datetime.now().isoformat(),
                })
            time.sleep(args.sleep_seconds)
        except Exception as exc:
            print(f"[FAILED FACEBOOK POSTS BATCH] {batch_index} | {exc}")

    if not args.dry_run:
        print(f"[FACEBOOK POSTS] Raw rows saved: {append_jsonl(rows, raw_path)}")
        print("[FACEBOOK POSTS] Next process command:")
        print(f"python data_pipeline\\src\\data_scraping\\facebook.py process-posts --raw-file \"{raw_path}\"")
    if args.process and not args.dry_run:
        args.raw_file = raw_path
        args.latest = False
        process_posts(args)


def find_source_for_post(raw_row: dict, fb2):
    sources = raw_row.get("sources") or []
    if not sources:
        return None
    if len(sources) == 1:
        return sources[0]
    item = raw_row.get("raw_item") or {}
    item_source_url = fb2.canonical_facebook_url(fb2.get_first(item, ["facebookUrl", "pageUrl", "sourceUrl", "inputUrl", "url"]))
    for source in sources:
        if fb2.canonical_facebook_url(source.get("source_url", "")) == item_source_url:
            return source
    return None


def process_posts(args: argparse.Namespace) -> None:
    fb2 = load_stage("02_facebook_posts.py", "facebook_posts_stage")
    raw_rows, input_files = read_raw_inputs(args.raw_dir, args.raw_file, args.latest)
    if not raw_rows:
        if POST_SEEDS_FILE.exists():
            print(f"[FACEBOOK POSTS] No raw rows found. Existing output kept: {POST_SEEDS_FILE}")
            return
        raise FileNotFoundError(f"No raw rows found in {args.raw_dir}")

    print_raw_inputs("FACEBOOK POSTS", raw_rows, input_files)

    rows = []
    reject_rows = []
    for raw_row in raw_rows:
        item = raw_row.get("raw_item") or {}
        source = find_source_for_post(raw_row, fb2)
        post_url = fb2.extract_post_url(item)
        if source is None:
            reject_rows.append({"post_url": post_url, "reject_reason": "cannot_map_source", "scraped_at": raw_row.get("scraped_at", "")})
            continue

        place_id = clean_text(source.get("place_id", ""))
        place_name = clean_text(source.get("place_name", ""))
        post_text = fb2.extract_post_text(item)
        comments_count = fb2.extract_comments_count(item)
        score = fb2.post_relevance_score(post_text, place_name, source.get("source_title", ""), source.get("source_snippet", ""))
        post = {
            "post_seed_id": fb2.make_id(place_id, post_url),
            "platform": "facebook",
            "place_id": place_id,
            "place_name": place_name,
            "source_id": clean_text(source.get("source_id", "")),
            "source_url": clean_text(source.get("source_url", "")),
            "source_type": clean_text(source.get("source_type", "")),
            "post_id": fb2.extract_post_id(item, post_url),
            "post_url": post_url,
            "post_text": post_text,
            "created_at": fb2.extract_created_at(item),
            "author_name": fb2.extract_author_name(item),
            "likes": fb2.extract_likes(item),
            "comments_count": comments_count,
            "shares": fb2.extract_shares(item),
            "post_relevance_score": score,
            "status": "new",
            "scraped_at": raw_row.get("scraped_at") or datetime.now().isoformat(),
        }
        keep, reason = fb2.should_keep_post(post, source)
        if keep:
            rows.append(post)
        else:
            reject = post.copy()
            reject["reject_reason"] = reason
            reject_rows.append(reject)

    seeds = pd.DataFrame(rows)
    if len(seeds) > 0:
        seeds = seeds.sort_values(by=["post_relevance_score", "comments_count", "likes"], ascending=[False, False, False])
        seeds = seeds.drop_duplicates(subset=["place_id", "post_url"], keep="first")

    rejects = pd.DataFrame(reject_rows)
    save_csv(seeds, POST_CANDIDATES_FILE, append=False, dedupe_subset=["place_id", "post_url"])
    saved = save_csv(seeds, POST_SEEDS_FILE, append=args.append, dedupe_subset=["place_id", "post_url"])
    save_csv(rejects, POST_REJECTIONS_FILE, append=args.append, dedupe_subset=["source_url", "post_url", "reject_reason"])
    print(f"[FACEBOOK POSTS] Seeds total: {len(saved)}")
    print(f"[FACEBOOK POSTS] Rejections: {POST_REJECTIONS_FILE}")


def load_comment_targets(args: argparse.Namespace, fb3) -> pd.DataFrame:
    place_ids = parse_place_ids(args.place_ids)
    targets = fb3.load_comment_targets(
        limit=args.limit_posts,
        include_direct=not args.no_direct_sources,
        place_ids=place_ids,
    )
    if place_ids and len(targets) > 0:
        targets = targets[targets["place_id"].astype(str).isin(place_ids)].copy()
    targets = limit_rows_per_place(targets, args.limit_posts_per_place)
    return targets


def crawl_comments(args: argparse.Namespace) -> None:
    fb3 = load_stage("03_facebook_comments.py", "facebook_comments_stage")
    fb3.COMMENTS_LIMIT_PER_POST = args.comments_limit
    targets = load_comment_targets(args, fb3)
    run_id = args.run_id or make_run_id("facebook_comments")
    raw_path = RAW_COMMENTS_DIR / f"{run_id}.jsonl"

    print(f"[FACEBOOK COMMENTS] Selected targets: {len(targets)}")
    print_place_counts("FACEBOOK COMMENTS", targets)
    rows = []
    batches = [targets.iloc[i:i + args.batch_size] for i in range(0, len(targets), args.batch_size)]
    for batch_index, batch in enumerate(batches, start=1):
        urls = [fb3.canonical_facebook_url(url) for url in batch["post_url"].tolist() if fb3.canonical_facebook_url(url)]
        if not urls:
            continue
        print(f"[FACEBOOK COMMENTS] Batch {batch_index}/{len(batches)} | urls={len(urls)}")
        if args.dry_run:
            continue
        try:
            items = fb3.run_comments_actor(urls)
            target_records = batch.to_dict(orient="records")
            for item in items:
                rows.append({
                    "run_id": run_id,
                    "platform": "facebook",
                    "stage": "comments",
                    "targets": target_records,
                    "raw_item": item,
                    "scraped_at": datetime.now().isoformat(),
                })
            time.sleep(args.sleep_seconds)
        except Exception as exc:
            print(f"[FAILED FACEBOOK COMMENTS BATCH] {batch_index} | {exc}")

    if not args.dry_run:
        print(f"[FACEBOOK COMMENTS] Raw rows saved: {append_jsonl(rows, raw_path)}")
        print("[FACEBOOK COMMENTS] Next process command:")
        print(f"python data_pipeline\\src\\data_scraping\\facebook.py process-comments --raw-file \"{raw_path}\"")
    if args.process and not args.dry_run:
        args.raw_file = raw_path
        args.latest = False
        process_comments(args)


def find_target_for_comment(raw_row: dict, fb3):
    targets = raw_row.get("targets") or []
    if not targets:
        return None
    if len(targets) == 1:
        return targets[0]
    item = raw_row.get("raw_item") or {}
    item_post_url = fb3.extract_comment_post_url(item)
    for target in targets:
        if fb3.canonical_facebook_url(target.get("post_url", "")) == item_post_url:
            return target
    return None


def process_comments(args: argparse.Namespace) -> None:
    fb3 = load_stage("03_facebook_comments.py", "facebook_comments_stage")
    raw_rows, input_files = read_raw_inputs(args.raw_dir, args.raw_file, args.latest)
    if not raw_rows:
        if COMMENTS_FILE.exists():
            print(f"[FACEBOOK COMMENTS] No raw rows found. Existing output kept: {COMMENTS_FILE}")
            return
        raise FileNotFoundError(f"No raw rows found in {args.raw_dir}")

    print_raw_inputs("FACEBOOK COMMENTS", raw_rows, input_files)

    rows = []
    for raw_row in raw_rows:
        item = raw_row.get("raw_item") or {}
        target = find_target_for_comment(raw_row, fb3)
        if target is None:
            continue

        comment_text = fb3.extract_comment_text(item)
        comment_author = fb3.extract_comment_author(item)
        comment_id = fb3.extract_comment_id(item)
        is_useful, reject_reason, quality, lang = fb3.classify_comment(
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
            "comment_author_url": fb3.extract_comment_author_url(item),
            "comment_likes": fb3.extract_comment_likes(item),
            "comment_created_at": fb3.extract_comment_created_at(item),
            "comment_depth": fb3.extract_comment_depth(item),
            "is_useful_comment": is_useful,
            "comment_quality_score": quality,
            "comment_language": lang,
            "comment_reject_reason": reject_reason,
            "scraped_at": raw_row.get("scraped_at") or datetime.now().isoformat(),
        })

    comments = pd.DataFrame(rows)
    if len(comments) > 0:
        comments = comments.drop_duplicates(subset=["id"], keep="last")
    elif COMMENTS_FILE.exists() and not args.append:
        print(f"[FACEBOOK COMMENTS] No processable comments found. Existing output kept: {COMMENTS_FILE}")
        return

    save_csv(comments, COMMENT_CANDIDATES_FILE, append=False, dedupe_subset=["id"])
    saved = save_csv(comments, COMMENTS_FILE, append=args.append, dedupe_subset=["id"])
    print(f"[FACEBOOK COMMENTS] Output: {COMMENTS_FILE}")
    print(f"[FACEBOOK COMMENTS] Rows total: {len(saved)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Raw-first Facebook scraping pipeline.")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("crawl", help="Run source, post, and comment stages as one command.")
    p.add_argument("--places-file", type=Path, default=MASTER_PLACES_FILE)
    p.add_argument("--place-ids", default="", help="Comma-separated place IDs, e.g. dalat_001,dalat_002.")
    p.add_argument("--start-row", type=int, default=1)
    p.add_argument("--end-row", type=int, default=None)
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--append", action="store_true", help="Append processed output to existing CSV files.")
    p.add_argument("--skip-google", action="store_true")
    p.add_argument("--skip-posts", action="store_true")
    p.add_argument("--skip-comments", action="store_true")
    p.add_argument("--include-groups", action="store_true")
    p.add_argument("--no-direct-sources", action="store_true")
    p.add_argument("--query-chunk-size", type=int, default=20)
    p.add_argument("--source-batch-size", type=int, default=1)
    p.add_argument("--comments-batch-size", type=int, default=1)
    p.add_argument("--limit-sources", type=int, default=None)
    p.add_argument("--limit-sources-per-place", type=int, default=2)
    p.add_argument("--limit-posts", type=int, default=None)
    p.add_argument("--limit-posts-per-place", type=int, default=3)
    p.add_argument("--comments-limit", type=int, default=100)
    p.add_argument("--sleep-seconds", type=int, default=2)
    p.add_argument("--run-id", default="")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=run_all)

    p = sub.add_parser("crawl-sources")
    p.add_argument("--places-file", type=Path, default=MASTER_PLACES_FILE)
    p.add_argument("--place-ids", default="")
    p.add_argument("--start-row", type=int, default=1)
    p.add_argument("--end-row", type=int, default=None)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--skip-google", action="store_true")
    p.add_argument("--query-chunk-size", type=int, default=20)
    p.add_argument("--sleep-seconds", type=int, default=2)
    p.add_argument("--run-id", default="")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--process", action="store_true")
    p.add_argument("--append", action="store_true")
    p.set_defaults(func=crawl_sources, raw_dir=RAW_SOURCES_DIR)

    p = sub.add_parser("process-sources")
    p.add_argument("--places-file", type=Path, default=MASTER_PLACES_FILE)
    p.add_argument("--raw-dir", type=Path, default=RAW_SOURCES_DIR)
    p.add_argument("--raw-file", default="", help="Process one specific raw source JSONL file.")
    p.add_argument("--latest", action="store_true", help="Process only the newest raw source JSONL file.")
    p.add_argument("--append", action="store_true")
    p.set_defaults(func=process_sources)

    p = sub.add_parser("crawl-posts")
    p.add_argument("--sources-file", type=Path, default=SOURCES_FILE)
    p.add_argument("--limit-sources", type=int, default=None)
    p.add_argument("--limit-sources-per-place", type=int, default=None)
    p.add_argument("--place-ids", default="")
    p.add_argument("--include-groups", action="store_true")
    p.add_argument("--source-batch-size", type=int, default=1)
    p.add_argument("--sleep-seconds", type=int, default=2)
    p.add_argument("--run-id", default="")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--process", action="store_true")
    p.add_argument("--append", action="store_true")
    p.set_defaults(func=crawl_posts, raw_dir=RAW_POSTS_DIR)

    p = sub.add_parser("process-posts")
    p.add_argument("--raw-dir", type=Path, default=RAW_POSTS_DIR)
    p.add_argument("--raw-file", default="", help="Process one specific raw posts JSONL file.")
    p.add_argument("--latest", action="store_true", help="Process only the newest raw posts JSONL file.")
    p.add_argument("--append", action="store_true")
    p.set_defaults(func=process_posts)

    p = sub.add_parser("crawl-comments")
    p.add_argument("--limit-posts", type=int, default=None)
    p.add_argument("--limit-posts-per-place", type=int, default=None)
    p.add_argument("--place-ids", default="")
    p.add_argument("--no-direct-sources", action="store_true")
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--comments-limit", type=int, default=100)
    p.add_argument("--sleep-seconds", type=int, default=2)
    p.add_argument("--run-id", default="")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--process", action="store_true")
    p.add_argument("--append", action="store_true")
    p.set_defaults(func=crawl_comments, raw_dir=RAW_COMMENTS_DIR)

    p = sub.add_parser("process-comments")
    p.add_argument("--raw-dir", type=Path, default=RAW_COMMENTS_DIR)
    p.add_argument("--raw-file", default="", help="Process one specific raw comments JSONL file.")
    p.add_argument("--latest", action="store_true", help="Process only the newest raw comments JSONL file.")
    p.add_argument("--append", action="store_true")
    p.set_defaults(func=process_comments)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
