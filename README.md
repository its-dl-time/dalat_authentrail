# INNOSTAR

Project for data collection, NLP processing, and web application development.

## Structure

```text
data_pipeline/
  data/                  Raw, interim, processed, and output datasets
  src/
    data_scraping/       Crawlers and external data collectors
    data_processing/     Cleaning, normalization, and dataset builders
backend/                 Backend application workspace
frontend/                Frontend application workspace
configs/                 Shared config files
docs/                    Notes and implementation references
```

## Common Commands

Clean Google Places exports:

```powershell
python data_pipeline\src\data_processing\clean_places.py
```

Crawl TikTok in chunks:

```powershell
python data_pipeline\src\data_scraping\tiktok.py crawl-videos --start-row 1 --limit 10
```

Run the full Facebook pipeline:

```powershell
python data_pipeline\src\data_scraping\facebook.py crawl --start-row 1 --limit 3 --append
```

Build cross-platform normalized datasets and place risk scores:

```powershell
python data_pipeline\src\data_processing\build_cross_platform_dataset.py
```

Vietnamese docs:

```text
docs/HUONG_DAN_CRAWL.md
docs/BANG_THAM_SO_LOC.md
```



