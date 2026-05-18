import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
INGESTION_DIR = Path(__file__).resolve().parent

PLACES_FILE = PROJECT_ROOT / "data" / "processed" / "places_master_top50.csv"
FACEBOOK_OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs" / "facebook"

STAGE_01_SOURCES = INGESTION_DIR / "01_facebook_gg.py"
STAGE_02_POSTS = INGESTION_DIR / "02_facebook_posts.py"
STAGE_03_COMMENTS = INGESTION_DIR / "03_facebook_comments.py"


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
        end_index = min(start_index + 3, total_rows)

    return places.iloc[start_index:end_index].copy()


def run_stage(command):
    print("\n" + "=" * 72)
    print("[PIPELINE] Running:")
    print(" ".join(str(part) for part in command))
    print("=" * 72)

    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Run Facebook source discovery, post discovery, and comment crawling "
            "as one pipeline for a selected chunk of the master places file."
        )
    )

    parser.add_argument("--places-file", default=str(PLACES_FILE))
    parser.add_argument("--output-dir", default=str(FACEBOOK_OUTPUT_DIR))
    parser.add_argument("--start-row", type=int, default=1)
    parser.add_argument("--end-row", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)

    parser.add_argument("--append-output", action="store_true")
    parser.add_argument("--skip-google", action="store_true")
    parser.add_argument("--skip-posts", action="store_true")
    parser.add_argument("--skip-comments", action="store_true")

    parser.add_argument("--limit-sources", type=int, default=None)
    parser.add_argument("--limit-posts", type=int, default=None)
    parser.add_argument("--include-groups", action="store_true")
    parser.add_argument("--no-direct-sources", action="store_true")
    parser.add_argument("--source-batch-size", type=int, default=1)
    parser.add_argument("--comments-batch-size", type=int, default=1)
    parser.add_argument("--comments-limit", type=int, default=100)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.end_row is not None and args.limit is not None:
        parser.error("Use either --end-row or --limit, not both.")

    places = pd.read_csv(args.places_file)
    selected_places = select_places_slice(
        places,
        start_row=args.start_row,
        end_row=args.end_row,
        limit=args.limit,
    )
    place_ids = [
        str(place_id).strip()
        for place_id in selected_places["place_id"].tolist()
        if str(place_id).strip()
    ]
    place_ids_arg = ",".join(place_ids)

    selected_start = selected_places.index.min() + 1 if len(selected_places) > 0 else 0
    selected_end = selected_places.index.max() + 1 if len(selected_places) > 0 else 0

    print("=" * 72)
    print("Facebook Unified Pipeline")
    print("=" * 72)
    print(f"Master file: {args.places_file}")
    print(f"Selected rows: {selected_start}-{selected_end}")
    print(f"Selected places: {len(selected_places)}")
    print(f"Place IDs: {place_ids_arg}")

    if len(selected_places) == 0:
        print("No places selected. Stop.")
        return

    stage_01 = [
        sys.executable,
        str(STAGE_01_SOURCES),
        "--places-file",
        str(args.places_file),
        "--output-dir",
        str(args.output_dir),
        "--start-row",
        str(args.start_row),
    ]

    if args.end_row is not None:
        stage_01.extend(["--end-row", str(args.end_row)])
    elif args.limit is not None:
        stage_01.extend(["--limit", str(args.limit)])

    if args.skip_google:
        stage_01.append("--skip-google")

    if args.append_output:
        stage_01.append("--append")

    run_stage(stage_01)

    if not args.skip_posts:
        stage_02 = [
            sys.executable,
            str(STAGE_02_POSTS),
            "--sources-file",
            str(Path(args.output_dir) / "facebook_sources.csv"),
            "--place-ids",
            place_ids_arg,
            "--source-batch-size",
            str(args.source_batch_size),
        ]

        if args.limit_sources is not None:
            stage_02.extend(["--limit-sources", str(args.limit_sources)])

        if args.include_groups:
            stage_02.append("--include-groups")

        if args.append_output:
            stage_02.append("--append")

        run_stage(stage_02)

    if not args.skip_comments:
        stage_03 = [
            sys.executable,
            str(STAGE_03_COMMENTS),
            "--place-ids",
            place_ids_arg,
            "--batch-size",
            str(args.comments_batch_size),
            "--comments-limit",
            str(args.comments_limit),
        ]

        if args.limit_posts is not None:
            stage_03.extend(["--limit-posts", str(args.limit_posts)])

        if args.no_direct_sources:
            stage_03.append("--no-direct-sources")

        if args.append_output:
            stage_03.append("--append")

        run_stage(stage_03)

    print("\n" + "=" * 72)
    print("Facebook pipeline completed.")
    print(f"Final comments: {Path(args.output_dir) / 'facebook_comments_output.csv'}")
    print("=" * 72)


if __name__ == "__main__":
    main()
