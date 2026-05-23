# HÆ°á»›ng Dáº«n Crawl Dá»¯ Liá»‡u

TÃ i liá»‡u nÃ y dÃ nh cho ngÆ°á»i phá»¥ trÃ¡ch crawl dá»¯ liá»‡u, khÃ´ng yÃªu cáº§u biáº¿t code. Má»¥c tiÃªu lÃ  cháº¡y Ä‘Ãºng lá»‡nh, biáº¿t file nÃ o Ä‘Æ°á»£c táº¡o ra, vÃ  biáº¿t khi nÃ o cáº§n dÃ¹ng `append` hoáº·c `process`.

ThÆ° má»¥c dá»± Ã¡n:

```powershell
cd D:\INNOSTAR
```

Náº¿u cÃ³ mÃ´i trÆ°á»ng áº£o Python:

```powershell
.\.venv\Scripts\activate
```

CÃ i thÆ° viá»‡n náº¿u má»›i clone dá»± Ã¡n hoáº·c Ä‘á»•i mÃ¡y:

```powershell
pip install -r requirements.txt
```

File `.env` á»Ÿ thÆ° má»¥c gá»‘c cáº§n cÃ³:

```env
APIFY_TOKEN=apify_api_xxxxxxxxxxxxxxxxx
```

File Ä‘á»‹a Ä‘iá»ƒm chuáº©n:

```text
data_pipeline/data/processed/places_master_top50.csv
```

CÃ³ 2 cÃ¡ch chá»n Ä‘á»‹a Ä‘iá»ƒm:

| CÃ¡ch chá»n | VÃ­ dá»¥ | Ã nghÄ©a |
|---|---|---|
| Theo dÃ²ng trong file master | `--start-row 1 --limit 5` | Láº¥y 5 Ä‘á»‹a Ä‘iá»ƒm Ä‘áº§u tiÃªn |
| Theo mÃ£ Ä‘á»‹a Ä‘iá»ƒm | `--place-ids dalat_001,dalat_002` | Chá»‰ crawl Ä‘Ãºng cÃ¡c Ä‘á»‹a Ä‘iá»ƒm nÃ y |

## NguyÃªn Táº¯c Chung

Má»—i ná»n táº£ng Ä‘á»u theo tÆ° duy raw-first:

```text
crawl   = gá»i Apify/API, tá»‘n credit, lÆ°u dá»¯ liá»‡u thÃ´ vÃ o data_pipeline/data/raw
process = lá»c vÃ  chuáº©n hÃ³a dá»¯ liá»‡u thÃ´, khÃ´ng tá»‘n Apify credit, ghi ra data_pipeline/data/outputs
```

NÃªn cháº¡y `--dry-run` trÆ°á»›c khi crawl tháº­t. `--dry-run` chá»‰ xem káº¿ hoáº¡ch, khÃ´ng gá»i API vÃ  khÃ´ng tá»‘n credit.

Khi crawl thÃªm batch má»›i, nÃªn dÃ¹ng `append` Ä‘á»ƒ giá»¯ káº¿t quáº£ cÅ©:

| Ná»n táº£ng | Tham sá»‘ append |
|---|---|
| Google Maps | `--append` khi process |
| Facebook | `--append` trong lá»‡nh `crawl` |
| TikTok | `--append-output` khi process |

Náº¿u khÃ´ng dÃ¹ng append, file output cÃ³ thá»ƒ bá»‹ ghi láº¡i theo batch má»›i.

## 1. Google Maps

Google Maps dÃ¹ng Ä‘á»ƒ láº¥y review trá»±c tiáº¿p cá»§a tá»«ng Ä‘á»‹a Ä‘iá»ƒm. ÄÃ¢y lÃ  nguá»“n review nÃªn Æ°u tiÃªn láº¥y nhiá»u nháº¥t cÃ³ thá»ƒ.

Script:

```text
data_pipeline/src/data_scraping/google_maps_reviews.py
```

### Tham Sá»‘ Cáº§n DÃ¹ng

| Tham sá»‘ | Ã nghÄ©a dá»… hiá»ƒu | Khi nÃ o dÃ¹ng |
|---|---|---|
| `--start-row` | Báº¯t Ä‘áº§u tá»« dÃ²ng thá»© máº¥y trong file 50 Ä‘á»‹a Ä‘iá»ƒm | Khi chia viá»‡c theo batch |
| `--limit` | Sá»‘ Ä‘á»‹a Ä‘iá»ƒm cáº§n crawl | ThÆ°á»ng dÃ¹ng `5`, `10`, hoáº·c `50` |
| `--reviews-per-place` | Sá»‘ review tá»‘i Ä‘a muá»‘n láº¥y cho má»—i Ä‘á»‹a Ä‘iá»ƒm | NÃªn dÃ¹ng `200` |
| `--dry-run` | Chá»‰ kiá»ƒm tra lá»‡nh, khÃ´ng crawl tháº­t | NÃªn cháº¡y trÆ°á»›c má»—i batch |
| `--append` | Gá»™p output má»›i vÃ o output cÅ© khi process | DÃ¹ng khi process thÃªm raw má»›i |

KhÃ´ng cáº§n quan tÃ¢m cÃ¡c tham sá»‘ khÃ¡c, há»‡ thá»‘ng Ä‘Ã£ Ä‘á»ƒ máº·c Ä‘á»‹nh.

### CÃ¡c BÆ°á»›c Crawl

BÆ°á»›c 1: kiá»ƒm tra trÆ°á»›c.

```powershell
python data_pipeline\src\data_scraping\google_maps_reviews.py crawl --start-row 1 --limit 5 --reviews-per-place 200 --dry-run
```

BÆ°á»›c 2: crawl tháº­t.

```powershell
python data_pipeline\src\data_scraping\google_maps_reviews.py crawl --start-row 1 --limit 5 --reviews-per-place 200
```

BÆ°á»›c 3: process raw thÃ nh output sáº¡ch.

```powershell
python data_pipeline\src\data_scraping\google_maps_reviews.py process --append
```

VÃ­ dá»¥ crawl Ä‘á»§ 50 Ä‘á»‹a Ä‘iá»ƒm:

```powershell
python data_pipeline\src\data_scraping\google_maps_reviews.py crawl --start-row 1 --limit 50 --reviews-per-place 200
python data_pipeline\src\data_scraping\google_maps_reviews.py process --append
```

### Output VÃ  CÃ¡ch Kiá»ƒm Tra

Raw data:

```text
data_pipeline/data/raw/google_maps/reviews/
```

Output sáº¡ch:

```text
data_pipeline/data/outputs/google_maps/google_maps_reviews_output.csv
```

Kiá»ƒm tra nhanh sá»‘ dÃ²ng:

```powershell
(Import-Csv data_pipeline\data\outputs\google_maps\google_maps_reviews_output.csv).Count
```

Kiá»ƒm tra báº±ng Excel/VS Code: má»Ÿ file `google_maps_reviews_output.csv`, xem cÃ³ cá»™t `place_id`, `review_text`, `rating` hay khÃ´ng.

### LÆ°u Ã Append VÃ  Process

- Crawl Google Maps táº¡o raw trong `data_pipeline/data/raw/google_maps/reviews/`.
- Process cÃ³ thá»ƒ cháº¡y láº¡i nhiá»u láº§n, khÃ´ng tá»‘n credit.
- Khi Ä‘Ã£ cÃ³ output cÅ© vÃ  muá»‘n cá»™ng thÃªm batch má»›i, dÃ¹ng `process --append`.

## 2. Facebook

Facebook Ä‘Ã£ Ä‘Æ°á»£c Ä‘Æ¡n giáº£n hÃ³a thÃ nh má»™t lá»‡nh chÃ­nh. NgÆ°á»i crawl chá»‰ cáº§n Ä‘Æ°a list Ä‘á»‹a Ä‘iá»ƒm hoáº·c chá»n dÃ²ng trong master file.

Script:

```text
data_pipeline/src/data_scraping/facebook.py
```

Lá»‡nh Facebook tá»± Ä‘á»™ng cháº¡y 3 táº§ng:

```text
source -> post -> comment
```

Trong Ä‘Ã³:

| Táº§ng | Há»‡ thá»‘ng lÃ m gÃ¬ |
|---|---|
| source | TÃ¬m link Facebook liÃªn quan tá»›i Ä‘á»‹a Ä‘iá»ƒm |
| post | Láº¥y bÃ i viáº¿t tá»« source náº¿u Facebook cho phÃ©p |
| comment | Láº¥y comment tá»« post/video/photo tÃ¬m Ä‘Æ°á»£c |

### Tham Sá»‘ Cáº§n DÃ¹ng

| Tham sá»‘ | Ã nghÄ©a dá»… hiá»ƒu | Khi nÃ o dÃ¹ng |
|---|---|---|
| `--place-ids` | Danh sÃ¡ch mÃ£ Ä‘á»‹a Ä‘iá»ƒm cáº§n crawl | CÃ¡ch Ä‘á»ƒ ngÆ°á»i crawl Ä‘Æ°a list Ä‘á»‹a Ä‘iá»ƒm rÃµ rÃ ng |
| `--start-row` | Báº¯t Ä‘áº§u tá»« dÃ²ng thá»© máº¥y trong file master | Khi chia viá»‡c theo batch |
| `--limit` | Sá»‘ Ä‘á»‹a Ä‘iá»ƒm cáº§n crawl tá»« `--start-row` | VÃ­ dá»¥ `--start-row 1 --limit 5` |
| `--append` | Gá»™p káº¿t quáº£ má»›i vÃ o output cÅ© | NÃªn dÃ¹ng khi crawl tháº­t |
| `--dry-run` | Xem trÆ°á»›c pipeline, khÃ´ng tá»‘n credit | NÃªn cháº¡y trÆ°á»›c khi crawl tháº­t |
| `--limit-sources-per-place` | Má»—i Ä‘á»‹a Ä‘iá»ƒm dÃ¹ng tá»‘i Ä‘a bao nhiÃªu source Ä‘á»ƒ crawl post | NÃªn dÃ¹ng `2` |
| `--limit-posts-per-place` | Má»—i Ä‘á»‹a Ä‘iá»ƒm crawl comment tá»« tá»‘i Ä‘a bao nhiÃªu post/video/photo | NÃªn dÃ¹ng `3` |
| `--comments-limit` | Sá»‘ comment tá»‘i Ä‘a má»—i post/video/photo | Test dÃ¹ng `20`, crawl tháº­t dÃ¹ng `100` |

KhÃ´ng cáº§n nháº¯c tá»›i cÃ¡c tham sá»‘ nÃ¢ng cao khÃ¡c trong lÃºc crawl bÃ¬nh thÆ°á»ng.

### CÃ¡c BÆ°á»›c Crawl

BÆ°á»›c 1: test trÆ°á»›c cho 2 Ä‘á»‹a Ä‘iá»ƒm.

```powershell
python data_pipeline\src\data_scraping\facebook.py crawl --place-ids dalat_001,dalat_002 --dry-run
```

BÆ°á»›c 2: crawl tháº­t theo list Ä‘á»‹a Ä‘iá»ƒm.

```powershell
python data_pipeline\src\data_scraping\facebook.py crawl --place-ids dalat_001,dalat_002,dalat_003 --append --limit-sources-per-place 2 --limit-posts-per-place 3 --comments-limit 100
```

BÆ°á»›c 3: hoáº·c crawl theo dÃ²ng trong master file.

```powershell
python data_pipeline\src\data_scraping\facebook.py crawl --start-row 1 --limit 5 --append --limit-sources-per-place 2 --limit-posts-per-place 3 --comments-limit 100
```

Khi cháº¡y, terminal sáº½ hiá»‡n log dáº¡ng nÃ y:

```text
[FACEBOOK SOURCES] Places: dalat_001:10, dalat_002:9
[FACEBOOK COMMENTS] Places: dalat_001:1, dalat_002:1
```

NghÄ©a lÃ  má»—i Ä‘á»‹a Ä‘iá»ƒm Ä‘Ã£ cÃ³ dá»¯ liá»‡u á»Ÿ tá»«ng táº§ng. Náº¿u thiáº¿u má»™t `place_id`, cÃ³ thá»ƒ láº§n crawl Ä‘Ã³ Google/Facebook khÃ´ng tráº£ source cho Ä‘á»‹a Ä‘iá»ƒm Ä‘Ã³.

### Output VÃ  CÃ¡ch Kiá»ƒm Tra

Raw data:

```text
data_pipeline/data/raw/facebook/sources/
data_pipeline/data/raw/facebook/posts/
data_pipeline/data/raw/facebook/comments/
```

Output sáº¡ch:

```text
data_pipeline/data/outputs/facebook/facebook_sources.csv
data_pipeline/data/outputs/facebook/facebook_post_seeds.csv
data_pipeline/data/outputs/facebook/facebook_post_rejections.csv
data_pipeline/data/outputs/facebook/facebook_comments_output.csv
```

File quan trá»ng nháº¥t:

```text
data_pipeline/data/outputs/facebook/facebook_comments_output.csv
```

Kiá»ƒm tra nhanh sá»‘ dÃ²ng:

```powershell
(Import-Csv data_pipeline\data\outputs\facebook\facebook_comments_output.csv).Count
```

Kiá»ƒm tra má»—i Ä‘á»‹a Ä‘iá»ƒm cÃ³ bao nhiÃªu comment:

```powershell
Import-Csv data_pipeline\data\outputs\facebook\facebook_comments_output.csv | Group-Object place_id | Select-Object Name,Count
```

Náº¿u comment Ã­t, kiá»ƒm tra source trÆ°á»›c:

```powershell
Import-Csv data_pipeline\data\outputs\facebook\facebook_sources.csv | Group-Object place_id | Select-Object Name,Count
```

### LÆ°u Ã Append VÃ  Process

- Vá»›i Facebook, ngÆ°á»i crawl nÃªn dÃ¹ng lá»‡nh `crawl` duy nháº¥t. Lá»‡nh nÃ y tá»± crawl vÃ  tá»± process.
- Khi crawl tháº­t, gáº§n nhÆ° luÃ´n thÃªm `--append`.
- Náº¿u quÃªn `--append`, output cÃ³ thá»ƒ bá»‹ ghi láº¡i theo batch má»›i.
- `facebook_post_seeds.csv` cÃ³ thá»ƒ Ã­t hoáº·c rá»—ng vÃ¬ Facebook page cÃ³ thá»ƒ cháº·n public post. ÄÃ¢y khÃ´ng nháº¥t thiáº¿t lÃ  lá»—i; náº¿u `facebook_comments_output.csv` váº«n cÃ³ data thÃ¬ pipeline váº«n Ä‘Ãºng.
- Náº¿u chá»‰ test, dÃ¹ng `--comments-limit 20` Ä‘á»ƒ tiáº¿t kiá»‡m. Khi crawl tháº­t, dÃ¹ng `--comments-limit 100`.

## 3. TikTok

TikTok cÃ³ 2 táº§ng:

```text
video seed -> comment
```

Seed video lÃ  video Ä‘Æ°á»£c chá»n lÃ m nguá»“n Ä‘á»ƒ crawl comment. KhÃ´ng pháº£i video nÃ o tÃ¬m tháº¥y cÅ©ng Ä‘Æ°á»£c giá»¯ láº¡i. Process video sáº½ lá»c theo Ä‘á»™ liÃªn quan vÃ  sá»‘ comment.

Script:

```text
data_pipeline/src/data_scraping/tiktok.py
```

### Tham Sá»‘ Cáº§n DÃ¹ng

| Tham sá»‘ | Ã nghÄ©a dá»… hiá»ƒu | Khi nÃ o dÃ¹ng |
|---|---|---|
| `--start-row` | Báº¯t Ä‘áº§u tá»« dÃ²ng thá»© máº¥y trong file master | Khi chia viá»‡c theo batch |
| `--limit` | Sá»‘ Ä‘á»‹a Ä‘iá»ƒm cáº§n crawl video | ThÆ°á»ng dÃ¹ng `5` hoáº·c `10` |
| `--dry-run` | Kiá»ƒm tra lá»‡nh, khÃ´ng crawl tháº­t | NÃªn cháº¡y trÆ°á»›c |
| `--latest` | Process file raw má»›i nháº¥t vá»«a crawl | DÃ¹ng sau má»—i láº§n crawl |
| `--append-output` | Gá»™p output má»›i vÃ o output cÅ© | DÃ¹ng khi crawl thÃªm batch má»›i |
| `--min-video-comments` | Video pháº£i cÃ³ Ã­t nháº¥t bao nhiÃªu comment má»›i Ä‘Æ°á»£c giá»¯ | Náº¿u Ã­t seed thÃ¬ háº¡ xuá»‘ng `5`; náº¿u nhiá»u seed rÃ¡c thÃ¬ tÄƒng lÃªn `15` |
| `--min-relevance-score` | Äiá»ƒm liÃªn quan tá»›i Ä‘á»‹a Ä‘iá»ƒm | ThÆ°á»ng dÃ¹ng `3.0` Ä‘áº¿n `3.5` |
| `--max-seed-videos-per-query` | Má»—i cÃ¢u tÃ¬m kiáº¿m giá»¯ tá»‘i Ä‘a bao nhiÃªu video | ThÆ°á»ng dÃ¹ng `3` |
| `--place-ids` | Chá»‰ crawl comment cho cÃ¡c Ä‘á»‹a Ä‘iá»ƒm nÃ y | NÃªn dÃ¹ng Ä‘á»ƒ khÃ´ng crawl nháº§m Ä‘á»‹a Ä‘iá»ƒm cÅ© |
| `--limit-videos` | Chá»‰ crawl comment tá»« má»™t sá»‘ video Ä‘áº§u tiÃªn | DÃ¹ng khi test |

KhÃ´ng cáº§n nháº¯c tá»›i cÃ¡c tham sá»‘ khÃ¡c trong lÃºc crawl bÃ¬nh thÆ°á»ng.

### CÃ¡c BÆ°á»›c Crawl

BÆ°á»›c 1: test crawl video.

```powershell
python data_pipeline\src\data_scraping\tiktok.py crawl-videos --start-row 1 --limit 5 --dry-run
```

BÆ°á»›c 2: crawl video raw.

```powershell
python data_pipeline\src\data_scraping\tiktok.py crawl-videos --start-row 1 --limit 5
```

BÆ°á»›c 3: process video thÃ nh seed.

```powershell
python data_pipeline\src\data_scraping\tiktok.py process-videos --latest --append-output --min-video-comments 10 --min-relevance-score 3.0 --max-seed-videos-per-query 3
```

BÆ°á»›c 4: crawl comment tá»« seed video. NÃªn truyá»n Ä‘Ãºng `place_id` cá»§a batch vá»«a crawl.

```powershell
python data_pipeline\src\data_scraping\tiktok.py crawl-comments --place-ids dalat_001,dalat_002,dalat_003,dalat_004,dalat_005
```

BÆ°á»›c 5: process comment.

```powershell
python data_pipeline\src\data_scraping\tiktok.py process-comments --latest --append-output
```

Test nhá» cho 1 Ä‘á»‹a Ä‘iá»ƒm vÃ  1 video:

```powershell
python data_pipeline\src\data_scraping\tiktok.py crawl-comments --place-ids dalat_001 --limit-videos 1 --dry-run
python data_pipeline\src\data_scraping\tiktok.py crawl-comments --place-ids dalat_001 --limit-videos 1
python data_pipeline\src\data_scraping\tiktok.py process-comments --latest --append-output
```

### Output VÃ  CÃ¡ch Kiá»ƒm Tra

Raw data:

```text
data_pipeline/data/raw/tiktok/videos/
data_pipeline/data/raw/tiktok/comments/
```

Output sáº¡ch:

```text
data_pipeline/data/outputs/tiktok/tiktok_video_seeds.csv
data_pipeline/data/outputs/tiktok/tiktok_video_rejections.csv
data_pipeline/data/outputs/tiktok/tiktok_comments_output.csv
data_pipeline/data/outputs/tiktok/tiktok_comment_rejections.csv
```

File quan trá»ng nháº¥t:

```text
data_pipeline/data/outputs/tiktok/tiktok_comments_output.csv
```

Kiá»ƒm tra sá»‘ seed video:

```powershell
(Import-Csv data_pipeline\data\outputs\tiktok\tiktok_video_seeds.csv).Count
```

Kiá»ƒm tra comment theo Ä‘á»‹a Ä‘iá»ƒm:

```powershell
Import-Csv data_pipeline\data\outputs\tiktok\tiktok_comments_output.csv | Group-Object place_id | Select-Object Name,Count
```

Kiá»ƒm tra video bá»‹ loáº¡i:

```text
data_pipeline/data/outputs/tiktok/tiktok_video_rejections.csv
```

### LÆ°u Ã Append VÃ  Process

- TikTok cáº§n process video trÆ°á»›c Ä‘á»ƒ táº¡o `tiktok_video_seeds.csv`, sau Ä‘Ã³ má»›i crawl comment.
- Khi crawl thÃªm batch má»›i, process video vÃ  process comment nÃªn cÃ³ `--append-output`.
- Khi crawl comment, nÃªn luÃ´n dÃ¹ng `--place-ids` cá»§a batch hiá»‡n táº¡i Ä‘á»ƒ khÃ´ng crawl láº¡i seed cá»§a Ä‘á»‹a Ä‘iá»ƒm cÅ©.
- Náº¿u seed quÃ¡ Ã­t, háº¡ `--min-video-comments` xuá»‘ng `5` hoáº·c háº¡ `--min-relevance-score` xuá»‘ng `3.0`.
- Náº¿u seed quÃ¡ nhiá»u vÃ  bá»‹ nhiá»…u, tÄƒng `--min-video-comments` lÃªn `15` hoáº·c `20`, vÃ  tÄƒng `--min-relevance-score` lÃªn `3.5` hoáº·c `4.0`.

## Kiá»ƒm Tra Sau Khi Crawl Xong

Kiá»ƒm tra nhanh cÃ¡c output chÃ­nh:

```powershell
(Import-Csv data_pipeline\data\outputs\google_maps\google_maps_reviews_output.csv).Count
(Import-Csv data_pipeline\data\outputs\facebook\facebook_comments_output.csv).Count
(Import-Csv data_pipeline\data\outputs\tiktok\tiktok_comments_output.csv).Count
```

Kiá»ƒm tra má»—i Ä‘á»‹a Ä‘iá»ƒm cÃ³ bao nhiÃªu dÃ²ng:

```powershell
Import-Csv data_pipeline\data\outputs\facebook\facebook_comments_output.csv | Group-Object place_id | Select-Object Name,Count
Import-Csv data_pipeline\data\outputs\tiktok\tiktok_comments_output.csv | Group-Object place_id | Select-Object Name,Count
```

Sau khi crawl xong 3 ná»n táº£ng, cháº¡y pipeline xá»­ lÃ½ tá»•ng há»£p:

```powershell
python data_pipeline\src\data_processing\build_cross_platform_dataset.py
python data_pipeline\src\data_processing\normalize_percent_outputs.py
```



