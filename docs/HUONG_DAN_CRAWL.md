# HƯỚNG DẪN CRAWL DỮ LIỆU

Tài liệu này dành cho người không biết code nhưng cần chạy crawl dữ liệu cho dự án INNOSTAR.

Mục tiêu đơn giản:

1. Lấy dữ liệu thô trước và lưu vào `data/raw`.
2. Process/lọc dữ liệu thô thành file sạch trong `data/outputs`.
3. Không crawl lại nếu chỉ muốn đổi ngưỡng lọc, vì process không tốn Apify credit.

## 1. Chuẩn Bị Một Lần Trước Khi Crawl

### Bước 1: Mở terminal trong thư mục dự án

Mở PowerShell, chạy:

```powershell
cd D:\INNOSTAR
```

### Bước 2: Kích hoạt môi trường Python nếu có

Nếu dự án có thư mục `.venv`, chạy:

```powershell
.\.venv\Scripts\activate
```

Nếu không có `.venv`, có thể bỏ qua bước này.

### Bước 3: Cài thư viện

Chạy:

```powershell
pip install -r requirements.txt
```

Chỉ cần làm lại khi đổi máy hoặc thiếu thư viện.

### Bước 4: Kiểm tra file `.env`

Trong thư mục `D:\INNOSTAR`, cần có file:

```text
.env
```

Trong file này phải có:

```env
APIFY_TOKEN=apify_api_xxxxxxxxxxxxxxxxx
```

Nếu thiếu token, crawler sẽ không chạy được.

### Bước 5: Kiểm tra file master địa điểm

File chuẩn hiện tại:

```text
data/processed/places_master_top50.csv
```

File này chứa 50 địa điểm cần crawl. Khi chạy lệnh có `--start-row` và `--limit`, hệ thống sẽ lấy địa điểm từ file này.

Ví dụ:

```text
--start-row 1 --limit 5
```

nghĩa là crawl 5 địa điểm đầu tiên.

```text
--start-row 6 --limit 5
```

nghĩa là crawl địa điểm số 6 đến số 10.

## 2. Nguyên Tắc Chạy Để Không Tốn Credit

Mỗi nền tảng đều nên chạy theo 2 bước:

```text
crawl  -> lấy dữ liệu thô, tốn Apify credit
process -> lọc dữ liệu thô, không tốn Apify credit
```

Luôn chạy `--dry-run` trước khi crawl thật nếu chưa chắc lệnh.

Ví dụ:

```powershell
python src\innostar\data_scraping\tiktok.py crawl-videos --start-row 1 --limit 5 --dry-run
```

Nếu thấy đúng số địa điểm/query thì bỏ `--dry-run` để crawl thật.

## 3. Google Maps Reviews

### Mục tiêu

Google Maps dùng để lấy review chính thống theo từng địa điểm.

Output cuối:

```text
data/outputs/google_maps/google_maps_reviews_output.csv
```

Raw lưu ở:

```text
data/raw/google_maps/reviews/
```

### Chạy Google Maps cho 5 địa điểm đầu

Kiểm tra trước:

```powershell
python src\innostar\data_scraping\google_maps_reviews.py crawl --start-row 1 --limit 5 --reviews-per-place 200 --dry-run
```

Crawl thật:

```powershell
python src\innostar\data_scraping\google_maps_reviews.py crawl --start-row 1 --limit 5 --reviews-per-place 200
```

Sau khi crawl xong, terminal sẽ hiện gợi ý file raw vừa tạo. Process file mới nhất:

```powershell
python src\innostar\data_scraping\google_maps_reviews.py process
```

### Tham số cần biết

| Tham số | Ý nghĩa | Gợi ý |
|---|---|---|
| `--start-row` | Dòng địa điểm bắt đầu trong master | Dùng để chia việc theo nhóm |
| `--limit` | Số địa điểm cần crawl | Nên crawl 5-10 địa điểm/lần |
| `--reviews-per-place` | Số review tối đa mỗi địa điểm | Mặc định nên dùng `200` |
| `--dry-run` | Chỉ xem kế hoạch, không crawl thật | Luôn dùng trước khi chạy thật |

### Ví dụ crawl đủ 50 địa điểm

```powershell
python src\innostar\data_scraping\google_maps_reviews.py crawl --start-row 1 --limit 50 --reviews-per-place 200
python src\innostar\data_scraping\google_maps_reviews.py process
```

## 4. Facebook

Facebook có 3 tầng:

```text
source -> post -> comment
```

Nghĩa là:

1. Tìm nguồn Facebook liên quan tới địa điểm.
2. Từ nguồn đó lấy bài post.
3. Từ bài post lấy comment.

Output cuối quan trọng nhất:

```text
data/outputs/facebook/facebook_comments_output.csv
```

Các output phụ:

```text
data/outputs/facebook/facebook_sources.csv
data/outputs/facebook/facebook_post_seeds.csv
data/outputs/facebook/facebook_post_rejections.csv
```

### Bước 1: Crawl source Facebook

Kiểm tra trước:

```powershell
python src\innostar\data_scraping\facebook.py crawl-sources --start-row 1 --limit 5 --dry-run
```

Crawl thật:

```powershell
python src\innostar\data_scraping\facebook.py crawl-sources --start-row 1 --limit 5
```

Process source mới nhất:

```powershell
python src\innostar\data_scraping\facebook.py process-sources --latest
```

Kết quả:

```text
data/outputs/facebook/facebook_sources.csv
```

### Bước 2: Crawl post từ source

Crawl post:

```powershell
python src\innostar\data_scraping\facebook.py crawl-posts
```

Process post mới nhất:

```powershell
python src\innostar\data_scraping\facebook.py process-posts --latest
```

Kết quả:

```text
data/outputs/facebook/facebook_post_seeds.csv
```

### Bước 3: Crawl comment từ post

Crawl comment:

```powershell
python src\innostar\data_scraping\facebook.py crawl-comments --comments-limit 100
```

Process comment mới nhất:

```powershell
python src\innostar\data_scraping\facebook.py process-comments --latest
```

Kết quả:

```text
data/outputs/facebook/facebook_comments_output.csv
```

### Cách crawl Facebook theo một nhóm địa điểm

Nếu chỉ muốn crawl một vài địa điểm cụ thể, dùng `--place-ids`.

Ví dụ:

```powershell
python src\innostar\data_scraping\facebook.py crawl-posts --place-ids dalat_001,dalat_002,dalat_003
python src\innostar\data_scraping\facebook.py process-posts --latest

python src\innostar\data_scraping\facebook.py crawl-comments --place-ids dalat_001,dalat_002,dalat_003 --comments-limit 100
python src\innostar\data_scraping\facebook.py process-comments --latest
```

### Tham số cần biết

| Tham số | Dùng ở bước | Ý nghĩa | Gợi ý |
|---|---|---|---|
| `--start-row` | `crawl-sources` | Dòng địa điểm bắt đầu | Dùng khi chia 50 địa điểm thành nhiều lượt |
| `--limit` | `crawl-sources` | Số địa điểm cần tìm source | Nên 5-10 địa điểm/lần |
| `--skip-google` | `crawl-sources` | Không tìm bằng Google Search, chỉ dùng link có sẵn | Tiết kiệm credit nhưng dễ thiếu source |
| `--place-ids` | `crawl-posts`, `crawl-comments` | Chỉ chạy cho một số địa điểm | Hữu ích khi crawl bù |
| `--limit-sources` | `crawl-posts` | Giới hạn số source đem crawl post | Dùng khi muốn tiết kiệm |
| `--limit-posts` | `crawl-comments` | Giới hạn số post đem crawl comment | Dùng khi test |
| `--comments-limit` | `crawl-comments` | Số comment tối đa mỗi post | Nên dùng `100` |
| `--source-batch-size` | `crawl-posts` | Số source mỗi lần gọi actor | Nên giữ `1` để tránh map sai |
| `--batch-size` | `crawl-comments` | Số post mỗi lần gọi actor | Nên giữ `1` để tránh map sai |
| `--latest` | `process-*` | Chỉ process raw file mới nhất | Nên dùng sau mỗi lần crawl |
| `--raw-file` | `process-*` | Process đúng một file raw cụ thể | Dùng khi muốn chắc chắn |
| `--append` | `process-*` | Gộp output mới với output cũ | Dùng khi crawl nhiều đợt |

### Flow Facebook khuyến nghị cho người crawl

Ví dụ crawl 5 địa điểm đầu:

```powershell
python src\innostar\data_scraping\facebook.py crawl-sources --start-row 1 --limit 5
python src\innostar\data_scraping\facebook.py process-sources --latest

python src\innostar\data_scraping\facebook.py crawl-posts
python src\innostar\data_scraping\facebook.py process-posts --latest

python src\innostar\data_scraping\facebook.py crawl-comments --comments-limit 100
python src\innostar\data_scraping\facebook.py process-comments --latest
```

Nếu muốn không ghi đè output cũ khi process nhiều đợt, thêm `--append`:

```powershell
python src\innostar\data_scraping\facebook.py process-sources --latest --append
python src\innostar\data_scraping\facebook.py process-posts --latest --append
python src\innostar\data_scraping\facebook.py process-comments --latest --append
```

## 5. TikTok

TikTok có 2 tầng:

```text
video seed -> comment
```

Seed video là video được chọn làm nguồn để crawl comment. Không phải video nào tìm được cũng dùng. Hệ thống sẽ lọc video theo độ liên quan và số comment.

Output cuối quan trọng nhất:

```text
data/outputs/tiktok/tiktok_comments_output.csv
```

Các output phụ:

```text
data/outputs/tiktok/tiktok_video_seeds.csv
data/outputs/tiktok/tiktok_video_rejections.csv
```

### Bước 1: Crawl video raw

Kiểm tra trước:

```powershell
python src\innostar\data_scraping\tiktok.py crawl-videos --start-row 1 --limit 5 --dry-run
```

Crawl thật:

```powershell
python src\innostar\data_scraping\tiktok.py crawl-videos --start-row 1 --limit 5
```

Process video mới nhất thành seed:

```powershell
python src\innostar\data_scraping\tiktok.py process-videos --latest
```

Kết quả:

```text
data/outputs/tiktok/tiktok_video_seeds.csv
```

### Bước 2: Crawl comment từ seed video

Crawl comment:

```powershell
python src\innostar\data_scraping\tiktok.py crawl-comments
```

Process comment mới nhất:

```powershell
python src\innostar\data_scraping\tiktok.py process-comments --latest
```

Kết quả:

```text
data/outputs/tiktok/tiktok_comments_output.csv
```

### Tham số cần biết

| Tham số | Dùng ở bước | Ý nghĩa | Gợi ý |
|---|---|---|---|
| `--start-row` | `crawl-videos` | Dòng địa điểm bắt đầu | Dùng để chia lượt crawl |
| `--limit` | `crawl-videos` | Số địa điểm cần crawl | Nên 5-10 địa điểm/lần |
| `--dry-run` | `crawl-videos`, `crawl-comments` | Chỉ xem kế hoạch, không crawl thật | Luôn dùng khi test |
| `--min-video-comments` | `process-videos` | Video phải có ít nhất bao nhiêu comment | Nên dùng `10` hoặc `15` |
| `--min-relevance-score` | `process-videos` | Điểm liên quan tối thiểu | Nên dùng `3.0` đến `3.5` |
| `--max-seed-videos-per-query` | `process-videos` | Mỗi query giữ tối đa bao nhiêu video | Nên dùng `2` hoặc `3` |
| `--max-seed-videos-total-per-place` | `process-videos` | Mỗi địa điểm giữ tối đa bao nhiêu seed video | Nên dùng `5` đến `10` |
| `--seeds-file` | `crawl-comments` | File video seed đầu vào | Mặc định là `tiktok_video_seeds.csv` |
| `--limit-videos` | `crawl-comments` | Chỉ crawl comment từ N video đầu | Dùng khi test |
| `--batch-size` | `crawl-comments` | Số video mỗi lần gọi actor | Mặc định `5` |
| `--min-quality-score` | `process-comments` | Comment phải đạt điểm chất lượng tối thiểu | Mặc định `0.2` |
| `--latest` | `process-*` | Chỉ process raw file mới nhất | Nên dùng sau mỗi lần crawl |
| `--raw-file` | `process-*` | Process đúng một file raw cụ thể | Dùng khi muốn chắc chắn |
| `--append-output` | `process-*` | Gộp output mới với output cũ | Dùng khi crawl nhiều đợt |

### Flow TikTok khuyến nghị cho người crawl

Ví dụ crawl 5 địa điểm đầu:

```powershell
python src\innostar\data_scraping\tiktok.py crawl-videos --start-row 1 --limit 5
python src\innostar\data_scraping\tiktok.py process-videos --latest

python src\innostar\data_scraping\tiktok.py crawl-comments
python src\innostar\data_scraping\tiktok.py process-comments --latest
```

Nếu seed quá ít, nới điều kiện:

```powershell
python src\innostar\data_scraping\tiktok.py process-videos --latest --min-video-comments 5 --min-relevance-score 3.0 --max-seed-videos-per-query 3 --max-seed-videos-total-per-place 10
```

Nếu seed bị nhiễu, siết điều kiện:

```powershell
python src\innostar\data_scraping\tiktok.py process-videos --latest --min-video-comments 20 --min-relevance-score 4.0 --max-seed-videos-per-query 1 --max-seed-videos-total-per-place 5
```

Nếu muốn không ghi đè output cũ khi process nhiều đợt, thêm `--append-output`:

```powershell
python src\innostar\data_scraping\tiktok.py process-videos --latest --append-output
python src\innostar\data_scraping\tiktok.py process-comments --latest --append-output
```

## 6. Kiểm Tra Kết Quả Sau Khi Crawl

Mở các file sau để xem dữ liệu:

Google Maps:

```text
data/outputs/google_maps/google_maps_reviews_output.csv
```

Facebook:

```text
data/outputs/facebook/facebook_sources.csv
data/outputs/facebook/facebook_post_seeds.csv
data/outputs/facebook/facebook_comments_output.csv
```

TikTok:

```text
data/outputs/tiktok/tiktok_video_seeds.csv
data/outputs/tiktok/tiktok_comments_output.csv
```

Nếu file output có ít dòng hơn mong đợi:

1. Kiểm tra raw có được tạo trong `data/raw/...` không.
2. Chạy lại process với `--latest`.
3. Với TikTok, nới `--min-video-comments` và `--min-relevance-score`.
4. Với Facebook, kiểm tra `facebook_sources.csv` có source cho địa điểm đó chưa.

## 7. Lệnh Nhanh Hay Dùng

Google Maps:

```powershell
python src\innostar\data_scraping\google_maps_reviews.py crawl --start-row 1 --limit 5 --reviews-per-place 200
python src\innostar\data_scraping\google_maps_reviews.py process
```

Facebook:

```powershell
python src\innostar\data_scraping\facebook.py crawl-sources --start-row 1 --limit 5
python src\innostar\data_scraping\facebook.py process-sources --latest
python src\innostar\data_scraping\facebook.py crawl-posts
python src\innostar\data_scraping\facebook.py process-posts --latest
python src\innostar\data_scraping\facebook.py crawl-comments --comments-limit 100
python src\innostar\data_scraping\facebook.py process-comments --latest
```

TikTok:

```powershell
python src\innostar\data_scraping\tiktok.py crawl-videos --start-row 1 --limit 5
python src\innostar\data_scraping\tiktok.py process-videos --latest
python src\innostar\data_scraping\tiktok.py crawl-comments
python src\innostar\data_scraping\tiktok.py process-comments --latest
```

