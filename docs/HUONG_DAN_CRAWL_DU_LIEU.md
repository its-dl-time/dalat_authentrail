# Hướng Dẫn Crawl Dữ Liệu Từ Số 0

Tài liệu này hướng dẫn người mới thiết lập API key, tạo master file địa điểm, crawl dữ liệu theo từng nền tảng, chọn số địa điểm mỗi lượt chạy, và hiểu các file đầu ra.

## 1. Chuẩn Bị Môi Trường

Chạy trong thư mục gốc project:

```powershell
cd D:\INNOSTAR
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Tạo file `.env` ở thư mục gốc:

```env
APIFY_TOKEN=apify_api_xxxxxxxxxxxxxxxxx
```

Không commit `.env` lên Git.

## 2. Lấy Apify API Token

1. Tạo hoặc đăng nhập tài khoản Apify.
2. Vào phần Settings hoặc Integrations/API.
3. Tạo/copy Personal API token.
4. Dán token vào file `.env` theo format ở trên.

Token chỉ dùng để xác thực. Chi phí/credit không cố định theo token, mà phụ thuộc actor nào được chạy, số lần chạy, số item, số review/comment/post/video lấy về.

Tham khảo tài liệu Apify chính thức: https://docs.apify.com/platform/integrations/api/

## 3. Cấu Trúc Dữ Liệu

```text
data/raw/google_places/          File raw export từ crawler Google Places
data/processed/                  File đã làm sạch, dùng làm input crawl
data/outputs/google_maps/        Review Google Maps
data/outputs/tiktok/             Video seed và comment TikTok
data/outputs/facebook/           Source, post seed và comment Facebook
```

File master quan trọng nhất:

```text
data/processed/places_master_top50.csv
```

Các cột quan trọng của master file:

| Cột | Ý nghĩa |
|---|---|
| `place_id` | ID nội bộ, ví dụ `dalat_001` |
| `title` | Tên địa điểm |
| `category` | Nhóm địa điểm |
| `address` | Địa chỉ |
| `google_maps_url` | URL Google Maps dùng để crawl review |
| `website`, `phone` | Thông tin tham khảo |
| `reviews_count`, `total_score` | Chỉ số đánh giá từ Google Places |

## 4. Tạo Master File Địa Điểm

Đặt các file raw Google Places export vào:

```text
data/raw/google_places/
```

Sau đó chạy:

```powershell
python src\innostar\data_processing\clean_places.py
```

Kết quả:

```text
data/processed/places_master_top50.csv
```

Mặc định script chọn top 50 địa điểm có từ `MIN_REVIEWS = 100` review trở lên.

## 5. Cách Chọn Địa Điểm Mỗi Lần Crawl

Các pipeline dùng dòng dữ liệu trong master file, tính từ `1` sau header CSV.

Ví dụ:

```powershell
--start-row 1 --limit 5
```

nghĩa là crawl 5 địa điểm đầu tiên: dòng 1 tới dòng 5.

```powershell
--start-row 6 --limit 5
```

nghĩa là crawl dòng 6 tới dòng 10.

TikTok và Facebook cũng hỗ trợ:

```powershell
--start-row 11 --end-row 20
```

Không dùng `--limit` và `--end-row` cùng lúc.

Khuyến nghị khi mới chạy:

| Mục tiêu | Số địa điểm/lượt |
|---|---:|
| Test pipeline lần đầu | 1 |
| Kiểm tra chất lượng output | 2-3 |
| Crawl ổn định, tiết kiệm credit | 5 |
| Crawl nhanh khi đã chắc config | 10+ |

Luôn dùng `--append` hoặc `--append-output` nếu muốn gom kết quả nhiều lượt vào cùng file.

## 6. Crawl Google Maps Reviews

Chạy:

```powershell
python src\innostar\data_ingestion\google_maps_reviews.py --start-row 1 --limit 5 --append
```

Tham số chính:

| Tham số | Ví dụ | Ý nghĩa |
|---|---|---|
| `--start-row` | `1` | Dòng bắt đầu trong master file |
| `--limit` | `5` | Số địa điểm cần crawl |
| `--append` | | Gộp kết quả vào file cũ và dedupe |

Constant trong code:

| Constant | Mặc định | Ý nghĩa |
|---|---:|---|
| `REVIEWS_PER_PLACE` | 20 | Số review tối đa mỗi địa điểm |
| `BATCH_SIZE` | 5 | Số địa điểm mỗi lần gọi actor |
| `SLEEP_SECONDS` | 2 | Nghỉ giữa các batch |

File output:

```text
data/outputs/google_maps/google_maps_reviews_output.csv
```

Nội dung chính:

| Cột | Ý nghĩa |
|---|---|
| `id` | ID review đã hash |
| `place_id`, `place_name`, `place_category` | Mapping về địa điểm |
| `google_maps_url` | URL địa điểm |
| `review_id`, `review_url` | ID/URL review |
| `review_text` | Nội dung review |
| `rating` | Số sao |
| `published_at` | Thời gian đăng |
| `reviewer_name`, `reviewer_id`, `reviewer_url` | Người review |
| `owner_response_text` | Phản hồi chủ địa điểm nếu có |

## 7. Crawl TikTok

Chạy theo chunk:

```powershell
python src\innostar\data_ingestion\tiktok.py --start-row 1 --limit 5 --append-output
```

Hoặc chọn khoảng dòng:

```powershell
python src\innostar\data_ingestion\tiktok.py --start-row 6 --end-row 10 --append-output
```

Luồng xử lý:

1. Search video TikTok theo tên địa điểm.
2. Lọc video đủ liên quan và đủ comment.
3. Crawl comment từ các video seed.
4. Lọc spam, reply của chủ shop/page, comment quá ngắn hoặc kém chất lượng.

Tham số/constant quan trọng:

| Constant | Mặc định | Gợi ý |
|---|---:|---|
| `QUERIES_PER_PLACE` | 2 | Giữ 2 để tiết kiệm, tăng 3 nếu thiếu video |
| `DISCOVERY_VIDEOS_PER_QUERY` | 20 | 10-20 để test, 20-50 khi crawl thật |
| `MAX_SEED_VIDEOS_PER_QUERY` | 1 | 1 tiết kiệm, 2-3 nếu muốn nhiều comment hơn |
| `COMMENTS_PER_VIDEO` | 10 | 10 test nhanh, 20-50 nếu cần NLP tốt hơn |
| `BATCH_COMMENT_URLS` | 5 | 5 ổn; giảm 1 nếu mapping actor không ổn |

File output:

```text
data/outputs/tiktok/tiktok_video_seeds.csv
data/outputs/tiktok/tiktok_comments_output.csv
data/outputs/tiktok/tiktok_video_rejections.csv
data/outputs/tiktok/tiktok_comment_rejections.csv
```

Nội dung chính của `tiktok_video_seeds.csv`:

| Cột | Ý nghĩa |
|---|---|
| `place_id`, `place_name` | Địa điểm |
| `query` | Query dùng để tìm video |
| `video_url`, `caption`, `author` | Thông tin video |
| `views`, `likes`, `shares`, `comment_count` | Engagement |
| `relevance_score` | Điểm liên quan |

Nội dung chính của `tiktok_comments_output.csv`:

| Cột | Ý nghĩa |
|---|---|
| `comment_text` | Nội dung comment |
| `is_useful_comment` | Có tín hiệu review hữu ích hay không |
| `comment_text_quality_score` | Điểm chất lượng text |
| `comment_is_likely_spam` | Có khả năng spam |
| `comment_language` | Ngôn ngữ ước lượng |
| `comment_emoji_ratio` | Tỷ lệ emoji |

## 8. Crawl Facebook

Nên dùng pipeline gộp:

```powershell
python src\innostar\data_ingestion\00_facebook_pipeline.py --start-row 1 --limit 3 --append-output
```

Hoặc:

```powershell
python src\innostar\data_ingestion\00_facebook_pipeline.py --start-row 4 --end-row 6 --append-output
```

Luồng xử lý:

1. `01_facebook_gg.py`: tìm Facebook source bằng link trong master và Google Search.
2. `02_facebook_posts.py`: crawl post từ page/profile/group source.
3. `03_facebook_comments.py`: crawl comment từ post seed và source direct.

Tham số pipeline chính:

| Tham số | Gợi ý | Ý nghĩa |
|---|---|---|
| `--start-row` | `1` | Dòng bắt đầu |
| `--limit` | `3` | Số địa điểm/lượt |
| `--append-output` | nên dùng | Gộp kết quả nhiều lượt |
| `--skip-google` | khi chỉ dùng link có sẵn | Bỏ Google Search để tiết kiệm |
| `--limit-sources` | `5-20` | Giới hạn source Facebook đem crawl post |
| `--limit-posts` | `10-50` | Giới hạn post đem crawl comment |
| `--source-batch-size` | `1` | Giữ 1 để tránh map sai source/place |
| `--comments-batch-size` | `1` | Giữ 1 nếu cần mapping chắc |
| `--comments-limit` | `100` | Số comment tối đa mỗi post |

File output:

```text
data/outputs/facebook/facebook_sources.csv
data/outputs/facebook/facebook_post_seeds.csv
data/outputs/facebook/facebook_post_rejections.csv
data/outputs/facebook/facebook_comments_output.csv
```

Nội dung chính:

| File | Nội dung |
|---|---|
| `facebook_sources.csv` | Link page/profile/post/reel/video tìm được cho từng địa điểm |
| `facebook_post_seeds.csv` | Post đủ liên quan và đủ comment để crawl tiếp |
| `facebook_post_rejections.csv` | Post bị loại và lý do |
| `facebook_comments_output.csv` | Comment cuối cùng, có điểm chất lượng và lý do loại nếu không hữu ích |

## 9. Ước Tính Credit/Token Trước Khi Chạy

Không thể ước tính chính xác chỉ từ `APIFY_TOKEN`. Token không chứa quota; quota phụ thuộc tài khoản Apify, actor, thời gian chạy và số item trả về. Cách ước tính thực tế là tính số lần gọi actor và giới hạn item.

Google Maps:

```text
Số actor runs xấp xỉ = ceil(số địa điểm / BATCH_SIZE)
Số review tối đa = số địa điểm * REVIEWS_PER_PLACE
```

Ví dụ `--limit 5`, `BATCH_SIZE=5`, `REVIEWS_PER_PLACE=20`:

```text
Khoảng 1 actor run, tối đa 100 review
```

TikTok:

```text
Search runs xấp xỉ = số địa điểm * QUERIES_PER_PLACE
Comment runs xấp xỉ = ceil(số video seed / BATCH_COMMENT_URLS)
Comment tối đa = số video seed * COMMENTS_PER_VIDEO
```

Ví dụ 5 địa điểm, 2 query/place, 1 video/query, 10 comment/video:

```text
Khoảng 10 search runs + 2 comment runs, tối đa khoảng 100 comment
```

Facebook:

```text
Google search runs xấp xỉ = ceil(số query / QUERY_CHUNK_SIZE)
Post runs xấp xỉ = ceil(số source được chọn / SOURCE_BATCH_SIZE)
Comment runs xấp xỉ = ceil(số post target / comments batch size)
Comment tối đa = số post target * comments_limit
```

Ví dụ 3 địa điểm, 2 query/place, `comments_limit=100`, tìm được 5 post target:

```text
Khoảng 1 Google Search run + vài post runs + 5 comment runs, tối đa 500 comment
```

## 10. Gợi Ý Cấu Hình Theo Mục Tiêu

| Mục tiêu | Google Maps | TikTok | Facebook |
|---|---|---|---|
| Test nhanh | `--limit 1`, 20 review/place | 1 địa điểm, 10 comment/video | 1 địa điểm, `--comments-limit 20` |
| Crawl tiết kiệm | 3-5 địa điểm/lượt | 3-5 địa điểm/lượt | 2-3 địa điểm/lượt |
| Crawl NLP tốt hơn | 20-50 review/place | 20-50 comment/video | 50-100 comment/post |
| Mapping chắc nhất | batch 1-5 | comment batch 1-5 | source/comment batch 1 |

## 11. Kiểm Tra Sau Khi Crawl

Mở các file CSV trong `data/outputs/...` và kiểm tra:

1. `place_id` có đúng với master file không.
2. Tỷ lệ `is_useful_comment` có quá thấp không.
3. Các file rejection có lý do loại quá nhiều ở một nhóm không.
4. Output có bị lặp không. Các script đã dedupe, nhưng vẫn nên kiểm tra nhanh.

Nếu output rỗng, thử giảm ngưỡng lọc trong code hoặc tăng số địa điểm/query/comment mỗi lượt.
