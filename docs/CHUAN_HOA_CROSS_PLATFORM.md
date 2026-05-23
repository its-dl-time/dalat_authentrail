# Handoff Chuáº©n HÃ³a Dá»¯ Liá»‡u Cross-Platform

TÃ i liá»‡u nÃ y tÃ³m táº¯t pháº§n xá»­ lÃ½ dá»¯ liá»‡u Ä‘Ã£ lÃ m Ä‘á»ƒ gom dá»¯ liá»‡u tá»« Google Maps, TikTok vÃ  Facebook vá» cÃ¹ng má»™t cáº¥u trÃºc, sau Ä‘Ã³ táº¡o bá»™ dá»¯ liá»‡u so sÃ¡nh chÃ©o theo tá»«ng Ä‘á»‹a Ä‘iá»ƒm.

Má»¥c tiÃªu hiá»‡n táº¡i lÃ  táº¡o báº£n MVP dá»… kiá»ƒm tra, dá»… cháº¡y láº¡i, chÆ°a dÃ¹ng AI/LLM phá»©c táº¡p. Output chÃ­nh lÃ  `risk_score` cho tá»«ng Ä‘á»‹a Ä‘iá»ƒm, kÃ¨m rating Google Maps Ä‘á»ƒ tham kháº£o.

## 1. Dá»¯ liá»‡u Ä‘áº§u vÃ o

Pipeline Ä‘ang dÃ¹ng 4 file chÃ­nh:

| File | Vai trÃ² |
|---|---|
| `data_pipeline/data/processed/places_master_top50.csv` | File master Ä‘á»‹a Ä‘iá»ƒm. ÄÃ¢y lÃ  nÆ¡i chá»©a `place_id`, tÃªn Ä‘á»‹a Ä‘iá»ƒm, danh má»¥c, Ä‘á»‹a chá»‰, tá»a Ä‘á»™, rating tá»•ng Google Maps. |
| `data_pipeline/data/outputs/google_maps/google_maps_reviews_output.csv` | Review Google Maps Ä‘Ã£ crawl. CÃ³ ná»™i dung review, rating sao, ngÆ°á»i review, sá»‘ like/helpful, Local Guide. |
| `data_pipeline/data/outputs/tiktok/tiktok_comments_output.csv` | Comment TikTok Ä‘Ã£ crawl tá»« cÃ¡c video liÃªn quan Ä‘á»‹a Ä‘iá»ƒm. CÃ³ ná»™i dung comment, like comment, thÃ´ng tin video, quality score. |
| `data_pipeline/data/outputs/facebook/facebook_comments_output.csv` | Comment Facebook Ä‘Ã£ crawl tá»« post/source liÃªn quan Ä‘á»‹a Ä‘iá»ƒm. CÃ³ ná»™i dung comment, like comment, post gá»‘c, quality score, reject reason. |

`place_id` lÃ  khÃ³a chÃ­nh Ä‘á»ƒ ná»‘i dá»¯ liá»‡u giá»¯a cÃ¡c ná»n táº£ng. VÃ­ dá»¥: `dalat_002`, `dalat_003`, `dalat_004`.

## 2. Nhá»¯ng gÃ¬ Ä‘Ã£ thá»±c hiá»‡n

ÄÃ£ táº¡o script:

```text
data_pipeline/src/data_processing/build_cross_platform_dataset.py
```

Script nÃ y lÃ m cÃ¡c bÆ°á»›c sau:

1. Äá»c file master Ä‘á»‹a Ä‘iá»ƒm vÃ  3 file output crawl.
2. TÃ¬m cÃ¡c Ä‘á»‹a Ä‘iá»ƒm cÃ³ Ä‘á»§ cáº£ 3 ná»n táº£ng Google Maps, TikTok, Facebook.
3. Vá»›i dá»¯ liá»‡u hiá»‡n táº¡i, MVP chá»‰ giá»¯:
   - `dalat_002`
   - `dalat_003`
   - `dalat_004`
4. XÃ³a dÃ²ng trÃ¹ng theo cá»™t `id` trong tá»«ng file nguá»“n.
5. Chuáº©n hÃ³a cÃ¡c cá»™t chung vá» má»™t schema thá»‘ng nháº¥t.
6. Giá»¯ cÃ¡c cá»™t riÃªng tá»«ng ná»n táº£ng trong file riÃªng.
7. Cháº¥m sentiment/topic/risk báº±ng rule-based Ä‘Æ¡n giáº£n.
8. Tá»•ng há»£p dá»¯ liá»‡u theo `place_id + platform`.
9. TÃ­nh `risk_score` cuá»‘i cÃ¹ng cho tá»«ng Ä‘á»‹a Ä‘iá»ƒm.

## 3. Pipeline hiá»‡n táº¡i

### BÆ°á»›c 1: Load vÃ  lá»c Ä‘á»‹a Ä‘iá»ƒm Ä‘á»§ ná»n táº£ng

Script Ä‘á»c dá»¯ liá»‡u tá»« 3 ná»n táº£ng, sau Ä‘Ã³ chá»‰ giá»¯ Ä‘á»‹a Ä‘iá»ƒm xuáº¥t hiá»‡n á»Ÿ cáº£ Google Maps, TikTok vÃ  Facebook.

LÃ½ do: so sÃ¡nh chÃ©o chá»‰ cÃ³ Ã½ nghÄ©a khi má»™t Ä‘á»‹a Ä‘iá»ƒm cÃ³ Ä‘á»§ dá»¯ liá»‡u tá»« nhiá»u nguá»“n.

### BÆ°á»›c 2: Chuáº©n hÃ³a dá»¯ liá»‡u chung

CÃ¡c nguá»“n cÃ³ tÃªn cá»™t khÃ¡c nhau, nÃªn script Ä‘Æ°a vá» cÃ¹ng má»™t bá»™ cá»™t.

VÃ­ dá»¥:

| Ã nghÄ©a | Google Maps | TikTok | Facebook | Cá»™t chuáº©n hÃ³a |
|---|---|---|---|---|
| Ná»™i dung | `review_text` | `comment_text` | `comment_text` | `content_text` |
| Thá»i gian Ä‘Äƒng | `published_at` | `comment_created_at` | `comment_created_at` | `content_created_at` |
| TÆ°Æ¡ng tÃ¡c | `likes_count` | `comment_likes` | `comment_likes` | `engagement_count` |
| NgÆ°á»i viáº¿t | `reviewer_id/name` | `comment_author` | `comment_author/url` | `author_id_or_name` |

File káº¿t quáº£:

```text
data_pipeline/data/processed/cross_platform/normalized_common_records.csv
```

ÄÃ¢y lÃ  file quan trá»ng nháº¥t náº¿u muá»‘n phÃ¢n tÃ­ch táº¥t cáº£ review/comment chung má»™t chá»—.

### BÆ°á»›c 3: Giá»¯ feature riÃªng tá»«ng ná»n táº£ng

KhÃ´ng pháº£i cá»™t nÃ o cÅ©ng so sÃ¡nh Ä‘Æ°á»£c giá»¯a cÃ¡c ná»n táº£ng.

VÃ­ dá»¥ Google Maps cÃ³ rating sao, TikTok cÃ³ view/like video, Facebook cÃ³ post gá»‘c vÃ  reject reason. Nhá»¯ng cá»™t nÃ y Ä‘Æ°á»£c giá»¯ riÃªng Ä‘á»ƒ khÃ´ng lÃ m rá»‘i file chung.

CÃ¡c file káº¿t quáº£:

```text
data_pipeline/data/processed/cross_platform/platform_google_maps_features.csv
data_pipeline/data/processed/cross_platform/platform_tiktok_features.csv
data_pipeline/data/processed/cross_platform/platform_facebook_features.csv
```

### BÆ°á»›c 4: Rule-based NLP MVP

Pipeline hiá»‡n táº¡i chÆ°a dÃ¹ng model AI. Script Ä‘ang dÃ¹ng rule Ä‘Æ¡n giáº£n Ä‘á»ƒ táº¡o cÃ¡c feature:

| Feature | Ã nghÄ©a |
|---|---|
| `sentiment_score` | Äiá»ƒm cáº£m xÃºc tá»« `-1` Ä‘áº¿n `1`. Ã‚m lÃ  tiÃªu cá»±c, dÆ°Æ¡ng lÃ  tÃ­ch cá»±c. |
| `service_score` | Ná»™i dung cÃ³ nháº¯c Ä‘áº¿n phá»¥c vá»¥/nhÃ¢n viÃªn/thÃ¡i Ä‘á»™ khÃ´ng. |
| `price_score` | Ná»™i dung cÃ³ nháº¯c Ä‘áº¿n giÃ¡/Ä‘áº¯t/ráº» khÃ´ng. |
| `scenery_score` | Ná»™i dung cÃ³ nháº¯c Ä‘áº¿n view/cáº£nh/check-in khÃ´ng. |
| `crowded_score` | Ná»™i dung cÃ³ nháº¯c Ä‘áº¿n Ä‘Ã´ng/chá» lÃ¢u/xáº¿p hÃ ng khÃ´ng. |
| `food_drink_score` | Ná»™i dung cÃ³ nháº¯c Ä‘áº¿n mÃ³n Äƒn/nÆ°á»›c/cafe khÃ´ng. |
| `cleanliness_score` | Ná»™i dung cÃ³ nháº¯c Ä‘áº¿n sáº¡ch/báº©n/vá»‡ sinh khÃ´ng. |
| `location_score` | Ná»™i dung cÃ³ nháº¯c Ä‘áº¿n Ä‘Æ°á»ng Ä‘i/vá»‹ trÃ­/gá»­i xe khÃ´ng. |
| `risk_flags` | CÃ¡c cá» rá»§i ro nhÆ° text rá»—ng, quÃ¡ ngáº¯n, nhiá»u emoji, spam, quáº£ng cÃ¡o. |

LÆ°u Ã½: Ä‘Ã¢y má»›i lÃ  báº£n MVP Ä‘á»ƒ cÃ³ pipeline cháº¡y Ä‘Æ°á»£c. Káº¿t quáº£ NLP chÆ°a pháº£i káº¿t quáº£ cuá»‘i cÃ¹ng Ä‘á»ƒ dÃ¹ng sáº£n pháº©m tháº­t.

### BÆ°á»›c 5: Tá»•ng há»£p theo Ä‘á»‹a Ä‘iá»ƒm vÃ  ná»n táº£ng

Sau khi chuáº©n hÃ³a tá»«ng dÃ²ng, script gom dá»¯ liá»‡u theo tá»«ng cáº·p:

```text
place_id + platform
```

VÃ­ dá»¥:

```text
dalat_002 + google_maps
dalat_002 + tiktok
dalat_002 + facebook
```

File káº¿t quáº£:

```text
data_pipeline/data/processed/cross_platform/place_platform_summary.csv
```

File nÃ y cho biáº¿t má»—i ná»n táº£ng Ä‘ang nÃ³i gÃ¬ vá» tá»«ng Ä‘á»‹a Ä‘iá»ƒm:

- CÃ³ bao nhiÃªu review/comment.
- Tá»· lá»‡ ná»™i dung há»¯u Ã­ch.
- Sentiment trung bÃ¬nh.
- Tá»· lá»‡ ná»™i dung tiÃªu cá»±c.
- Tá»· lá»‡ record bá»‹ gáº¯n cá» rá»§i ro.
- Äiá»ƒm topic trung bÃ¬nh.
- Vá»›i Google Maps cÃ³ thÃªm rating trung bÃ¬nh tá»« review vÃ  rating master.

### BÆ°á»›c 6: TÃ­nh risk score theo Ä‘á»‹a Ä‘iá»ƒm

Script táº¡o file cuá»‘i:

```text
data_pipeline/data/processed/cross_platform/place_cross_platform_risk.csv
```

Má»—i dÃ²ng lÃ  má»™t Ä‘á»‹a Ä‘iá»ƒm.

CÃ¡c cá»™t chÃ­nh:

| Cá»™t | Ã nghÄ©a |
|---|---|
| `place_id` | ID Ä‘á»‹a Ä‘iá»ƒm. |
| `place_name` | TÃªn Ä‘á»‹a Ä‘iá»ƒm. |
| `google_maps_rating` | Rating Google Maps tá»« master file. |
| `risk_score` | Äiá»ƒm rá»§i ro tá»« `0` Ä‘áº¿n `1`. CÃ ng cao cÃ ng rá»§i ro. |
| `risk_level` | Má»©c rá»§i ro: `low`, `medium`, `high`. |
| `data_quality_risk` | Rá»§i ro do dá»¯ liá»‡u nhiá»u text ngáº¯n, spam, reject, low quality. |
| `sentiment_gap` | Äá»™ lá»‡ch cáº£m xÃºc giá»¯a cÃ¡c ná»n táº£ng. |
| `negative_social_vs_maps_gap` | Social tiÃªu cá»±c trong khi Google Maps váº«n cao. |
| `topic_gap` | Chá»§ Ä‘á» bá»‹ lá»‡ch giá»¯a cÃ¡c ná»n táº£ng. |
| `engagement_gap` | TÆ°Æ¡ng tÃ¡c lá»‡ch giá»¯a cÃ¡c ná»n táº£ng. |
| `coverage_risk` | Rá»§i ro do tá»· lá»‡ ná»™i dung há»¯u Ã­ch tháº¥p. |

Thang Ä‘iá»ƒm:

| Risk score | Risk level | Diá»…n giáº£i |
|---:|---|---|
| `< 0.33` | `low` | Ãt dáº¥u hiá»‡u rá»§i ro. |
| `0.33 - < 0.66` | `medium` | CÃ³ dáº¥u hiá»‡u cáº§n kiá»ƒm tra thÃªm. |
| `>= 0.66` | `high` | Rá»§i ro cao, nÃªn xem ká»¹ dá»¯ liá»‡u gá»‘c. |

## 4. HÆ°á»›ng dáº«n cháº¡y cho ngÆ°á»i chÆ°a biáº¿t code

### BÆ°á»›c 1: Má»Ÿ terminal

Má»Ÿ PowerShell hoáº·c terminal trong thÆ° má»¥c project:

```powershell
cd D:\INNOSTAR
```

### BÆ°á»›c 2: CÃ i thÆ° viá»‡n náº¿u chÆ°a cÃ i

Chá»‰ cáº§n cháº¡y má»™t láº§n:

```powershell
pip install -r requirements.txt
```

Náº¿u Ä‘ang dÃ¹ng mÃ´i trÆ°á»ng áº£o `.venv`, kÃ­ch hoáº¡t trÆ°á»›c:

```powershell
.\.venv\Scripts\activate
```

Sau Ä‘Ã³ cháº¡y láº¡i:

```powershell
pip install -r requirements.txt
```

### BÆ°á»›c 3: Cháº¡y pipeline chuáº©n hÃ³a

Cháº¡y lá»‡nh:

```powershell
python data_pipeline\src\data_processing\build_cross_platform_dataset.py
```

Náº¿u cháº¡y thÃ nh cÃ´ng, terminal sáº½ hiá»‡n kiá»ƒu nhÆ°:

```text
Cross-platform dataset built.
Complete places: dalat_002, dalat_003, dalat_004
Normalized records: 819
Place-platform summary rows: 9
Risk rows: 3
```

### BÆ°á»›c 4: Xem káº¿t quáº£

Má»Ÿ thÆ° má»¥c:

```text
data_pipeline/data/processed/cross_platform/
```

File nÃªn xem Ä‘áº§u tiÃªn:

```text
place_cross_platform_risk.csv
```

File nÃ y lÃ  káº¿t quáº£ cuá»‘i theo tá»«ng Ä‘á»‹a Ä‘iá»ƒm.

Náº¿u muá»‘n xem dá»¯ liá»‡u chi tiáº¿t tá»«ng comment/review sau chuáº©n hÃ³a, má»Ÿ:

```text
normalized_common_records.csv
```

## 5. CÃ¡c file output cá»¥ thá»ƒ lÃ m gÃ¬

| File | DÃ¹ng Ä‘á»ƒ lÃ m gÃ¬ |
|---|---|
| `normalized_common_records.csv` | Dá»¯ liá»‡u chung Ä‘Ã£ chuáº©n hÃ³a tá»« cáº£ 3 ná»n táº£ng, má»—i dÃ²ng lÃ  má»™t review/comment. |
| `platform_google_maps_features.csv` | Feature riÃªng cá»§a Google Maps nhÆ° rating, Local Guide, reviewer review count, owner response. |
| `platform_tiktok_features.csv` | Feature riÃªng cá»§a TikTok nhÆ° video URL, caption, view, like video, comment count. |
| `platform_facebook_features.csv` | Feature riÃªng cá»§a Facebook nhÆ° source URL, post URL, post relevance, comment depth, reject reason. |
| `place_platform_summary.csv` | Báº£ng tá»•ng há»£p theo tá»«ng Ä‘á»‹a Ä‘iá»ƒm vÃ  tá»«ng ná»n táº£ng. |
| `place_cross_platform_risk.csv` | Báº£ng risk score cuá»‘i cÃ¹ng theo tá»«ng Ä‘á»‹a Ä‘iá»ƒm. |

## 6. Nhá»¯ng viá»‡c cáº§n lÃ m tiáº¿p theo

Pipeline hiá»‡n táº¡i Ä‘Ã£ cháº¡y Ä‘Æ°á»£c end-to-end, nhÆ°ng Ä‘á»ƒ Ä‘áº¡t Ä‘Ãºng má»¥c tiÃªu ban Ä‘áº§u thÃ¬ cáº§n tá»‘i Æ°u thÃªm cÃ¡c pháº§n sau.

### 6.1. NÃ¢ng cáº¥p NLP sentiment

Hiá»‡n táº¡i sentiment Ä‘ang dá»±a trÃªn tá»« khÃ³a Ä‘Æ¡n giáº£n. Cáº§n nÃ¢ng cáº¥p Ä‘á»ƒ hiá»ƒu ngá»¯ cáº£nh tá»‘t hÆ¡n.

VÃ­ dá»¥ khÃ³:

- "View Ä‘áº¹p nhÆ°ng phá»¥c vá»¥ quÃ¡ tá»‡"
- "KhÃ´ng tá»‡ nha"
- "QuÃ¡n nÃ y Ä‘Ã´ng kinh khá»§ng nhÆ°ng Ä‘Ã¡ng thá»­"
- Comment dÃ¹ng tiáº¿ng lÃ³ng, viáº¿t táº¯t, má»‰a mai.

HÆ°á»›ng tá»‘i Æ°u:

1. Táº¡o táº­p dá»¯ liá»‡u máº«u Ä‘Ã£ gÃ¡n nhÃ£n thá»§ cÃ´ng.
2. GÃ¡n nhÃ£n sentiment: tÃ­ch cá»±c, trung tÃ­nh, tiÃªu cá»±c, mixed.
3. DÃ¹ng model NLP/LLM Ä‘á»ƒ phÃ¢n loáº¡i.
4. So sÃ¡nh káº¿t quáº£ model vá»›i rule hiá»‡n táº¡i.

### 6.2. NÃ¢ng cáº¥p topic extraction

Topic hiá»‡n táº¡i cÅ©ng Ä‘ang dá»±a trÃªn tá»« khÃ³a. NÃªn nÃ¢ng cáº¥p Ä‘á»ƒ báº¯t Ä‘Æ°á»£c Ã½ nghÄ©a dÃ¹ ngÆ°á»i dÃ¹ng khÃ´ng dÃ¹ng Ä‘Ãºng tá»« khÃ³a.

VÃ­ dá»¥:

- "NhÃ¢n viÃªn khÃ´ng thÃ¨m nhÃ¬n khÃ¡ch" nÃªn thuá»™c topic service.
- "Ly nÃ y 80k hÆ¡i Ä‘au vÃ­" nÃªn thuá»™c topic price.
- "ÄÆ°á»ng vÃ o hÆ¡i khÃ³ kiáº¿m" nÃªn thuá»™c topic location.

HÆ°á»›ng tá»‘i Æ°u:

1. Chá»‘t taxonomy topic cá»‘ Ä‘á»‹nh.
2. GÃ¡n nhÃ£n topic cho má»™t táº­p comment/review máº«u.
3. DÃ¹ng embedding hoáº·c LLM Ä‘á»ƒ phÃ¢n loáº¡i topic.
4. Cho phÃ©p má»™t review/comment cÃ³ nhiá»u topic cÃ¹ng lÃºc.

### 6.3. TÃ¡ch comment tháº­t sá»± cÃ³ giÃ¡ trá»‹ review

TikTok/Facebook cÃ³ nhiá»u comment khÃ´ng pháº£i review tháº­t, vÃ­ dá»¥:

- Tag báº¡n bÃ¨.
- Emoji.
- "Xin Ä‘á»‹a chá»‰"
- "Äáº¹p quÃ¡"
- Comment Ä‘Ã¹a hoáº·c khÃ´ng liÃªn quan.

Cáº§n cáº£i thiá»‡n `is_useful` Ä‘á»ƒ chá»‰ giá»¯ ná»™i dung cÃ³ tÃ­n hiá»‡u tráº£i nghiá»‡m tháº­t.

HÆ°á»›ng tá»‘i Æ°u:

1. Táº¡o nhÃ£n `useful_review`, `not_review`, `question`, `spam`, `owner_reply`.
2. DÃ¹ng model phÃ¢n loáº¡i.
3. Khi tÃ­nh risk, giáº£m trá»ng sá»‘ nhá»¯ng comment khÃ´ng pháº£i review tháº­t.

### 6.4. Tá»‘i Æ°u cÃ´ng thá»©c risk score

CÃ´ng thá»©c hiá»‡n táº¡i lÃ  MVP cÃ³ trá»ng sá»‘ thá»§ cÃ´ng.

CÃ¡c thÃ nh pháº§n Ä‘ang dÃ¹ng:

- `data_quality_risk`
- `sentiment_gap`
- `negative_social_vs_maps_gap`
- `topic_gap`
- `engagement_gap`
- `coverage_risk`

Cáº§n tá»‘i Æ°u báº±ng cÃ¡ch:

1. Review thá»§ cÃ´ng má»™t sá»‘ Ä‘á»‹a Ä‘iá»ƒm.
2. Xem risk score cÃ³ há»£p lÃ½ khÃ´ng.
3. Äiá»u chá»‰nh trá»ng sá»‘.
4. CÃ³ thá»ƒ tÃ¡ch risk thÃ nh nhiá»u loáº¡i:
   - Risk do seeding.
   - Risk do cháº¥t lÆ°á»£ng dá»‹ch vá»¥.
   - Risk do dá»¯ liá»‡u thiáº¿u.
   - Risk do lá»‡ch giá»¯a cÃ¡c ná»n táº£ng.

### 6.5. Bá»• sung dá»¯ liá»‡u thiáº¿u ná»n táº£ng

Hiá»‡n MVP chá»‰ tÃ­nh Ä‘á»‹a Ä‘iá»ƒm cÃ³ Ä‘á»§ 3 ná»n táº£ng.

Vá» sau nÃªn xá»­ lÃ½ cáº£ Ä‘á»‹a Ä‘iá»ƒm thiáº¿u 1-2 ná»n táº£ng báº±ng `coverage_risk`, nhÆ°ng cáº§n quy Ä‘á»‹nh rÃµ:

- Thiáº¿u TikTok cÃ³ bá»‹ pháº¡t khÃ´ng?
- Thiáº¿u Facebook cÃ³ bá»‹ pháº¡t khÃ´ng?
- Google Maps cÃ³ pháº£i nguá»“n báº¯t buá»™c khÃ´ng?
- Bao nhiÃªu review/comment lÃ  Ä‘á»§ tin cáº­y?

### 6.6. ThÃªm embedding similarity Ä‘á»ƒ phÃ¡t hiá»‡n seeding

Trong plan ban Ä‘áº§u cÃ³ pháº§n phÃ¡t hiá»‡n ná»™i dung láº·p, paraphrase, template spam.

Hiá»‡n táº¡i chÆ°a lÃ m pháº§n nÃ y.

HÆ°á»›ng tá»‘i Æ°u:

1. Táº¡o embedding cho tá»«ng review/comment.
2. So sÃ¡nh Ä‘á»™ giá»‘ng nhau trong cÃ¹ng má»™t Ä‘á»‹a Ä‘iá»ƒm.
3. Náº¿u nhiá»u ná»™i dung ráº¥t giá»‘ng nhau, tÄƒng seeding risk.
4. So sÃ¡nh theo cá»¥m topic, khÃ´ng chá»‰ so tá»«ng cÃ¢u.

### 6.7. ThÃªm kiá»ƒm thá»­ tá»± Ä‘á»™ng

Hiá»‡n Ä‘Ã£ kiá»ƒm tra thá»§ cÃ´ng sau khi cháº¡y script.

NÃªn thÃªm test tá»± Ä‘á»™ng Ä‘á»ƒ Ä‘áº£m báº£o:

- Output luÃ´n cÃ³ Ä‘Ãºng cá»™t.
- KhÃ´ng máº¥t `place_id`.
- `risk_score` luÃ´n náº±m trong `[0, 1]`.
- Chá»‰ Ä‘á»‹a Ä‘iá»ƒm Ä‘á»§ ná»n táº£ng má»›i vÃ o MVP output.
- Dá»¯ liá»‡u thiáº¿u text/rating/engagement khÃ´ng lÃ m pipeline lá»—i.

## 7. Ghi chÃº vá» Git

CÃ¡c file dá»¯ liá»‡u máº«u chÃ­nh Ä‘Ã£ Ä‘Æ°á»£c má»Ÿ trong `.gitignore` Ä‘á»ƒ cÃ³ thá»ƒ push lÃªn git:

- `.env`
- `data_pipeline/data/processed/places_master_top50.csv`
- `data_pipeline/data/outputs/google_maps/google_maps_reviews_output.csv`
- `data_pipeline/data/outputs/tiktok/tiktok_comments_output.csv`
- `data_pipeline/data/outputs/facebook/facebook_comments_output.csv`
- `data_pipeline/data/processed/cross_platform/*.csv`

CÃ¡c thÆ° má»¥c váº«n nÃªn bá» qua:

- `.venv/`
- `__pycache__/`
- file raw Google Places lá»›n trong `data_pipeline/data/raw/google_places/`
- model/cache/log táº¡m

TrÆ°á»›c khi push, nÃªn má»Ÿ `.env` kiá»ƒm tra cháº¯c cháº¯n khÃ´ng cÃ²n API key tháº­t.



