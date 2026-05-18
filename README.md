# INNOSTAR

Project for data collection, NLP processing, and web application development.

## Structure

```text
data/
  raw/                   Original crawler exports
  processed/             Cleaned datasets used by pipelines and models
  outputs/               Generated pipeline outputs and crawl results
docs/                    Notes, PDFs, and implementation references
src/innostar/
  data_ingestion/        Crawlers and external data collectors
  data_processing/       Cleaning, normalization, and dataset builders
  nlp/                   NLP preprocessing, training, and inference code
  web/                   Shared web-facing Python modules
```

## Common Commands

Clean Google Places exports:

```powershell
python src\innostar\data_processing\clean_places.py
```

Crawl TikTok in chunks:

```powershell
python src\innostar\data_ingestion\tiktok.py --start-row 1 --limit 10 --append-output
```

Run the full Facebook pipeline:

```powershell
python src\innostar\data_ingestion\00_facebook_pipeline.py --start-row 1 --limit 3 --append-output
```

Vietnamese docs:

```text
docs/HUONG_DAN_CRAWL_DU_LIEU.md
docs/BANG_THAM_SO_LOC.md
```
