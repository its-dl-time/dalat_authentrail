# Hướng Dẫn Crawl Dữ Liệu

Tài liệu này dành cho người phụ trách crawl dữ liệu, không yêu cầu biết code. Mục tiêu là chạy đúng lệnh, biết file nào được tạo ra, và biết khi nào cần dùng `append` hoặc `process`.

Thư mục dự án:

```powershell
cd {đường dẫn tới dự án của bạn}
```
Kiểm tra coi có git chưa, nếu chưa có thì cài.

```powershell
git --version
```
Nếu có môi trường ảo Python:

```powershell
.\.venv\Scripts\activate
```

Cài thư viện nếu mới clone dự án hoặc đổi máy:

```powershell
pip install -r requirements.txt
```

File `.env` ở thư mục gốc cần có:

```env
APIFY_TOKEN=apify_api_xxxxxxxxxxxxxxxxx
```

File địa điểm chuẩn:

```text
data_pipeline/data/processed/places_master_top50.csv
```

Có 2 cách chọn địa điểm:

| Cách chọn | Ví dụ | Ý nghĩa |
|---|---|---|
| Theo dòng trong file master | `--start-row 1 --limit 5` | Lấy 5 địa điểm đầu tiên |
| Theo mã địa điểm | `--place-ids dalat_001,dalat_002` | Chỉ crawl đúng các địa điểm này |

## Nguyên Tắc Chung

Mỗi nền tảng đều theo tư duy raw-first:

```text
crawl   = gọi Apify/API, tốn credit, lưu dữ liệu thô vào data_pipeline/data/raw
process = lọc và chuẩn hóa dữ liệu thô, không tốn Apify credit, ghi ra data_pipeline/data/outputs
```

Nên chạy `--dry-run` trước khi crawl thật. `--dry-run` chỉ xem kế hoạch, không gọi API và không tốn credit.

Khi crawl thêm batch mới, nên dùng `append` để giữ kết quả cũ:

| Nền tảng | Tham số append |
|---|---|
| Google Maps | `--append` khi process |
| Facebook | `--append` trong lệnh `crawl` |
| TikTok | `--append-output` khi process |

Nếu không dùng append, file output có thể bị ghi lại theo batch mới.

## 1. Google Maps

Google Maps dùng để lấy review trực tiếp của từng địa điểm. Đây là nguồn review nên ưu tiên lấy nhiều nhất có thể.

Script:

```text
data_pipeline/src/data_scraping/google_maps_reviews.py
```

### Tham Số Cần Dùng

| Tham số | Ý nghĩa dễ hiểu | Khi nào dùng |
|---|---|---|
| `--start-row` | Bắt đầu từ dòng thứ mấy trong file 50 địa điểm | Khi chia việc theo batch |
| `--limit` | Số địa điểm cần crawl | Thường dùng `5`, `10`, hoặc `50` |
| `--reviews-per-place` | Số review tối đa muốn lấy cho mỗi địa điểm | Nên dùng `200` |
| `--dry-run` | Chỉ kiểm tra lệnh, không crawl thật | Nên chạy trước mỗi batch |
| `--append` | Gộp output mới vào output cũ khi process | Dùng khi process thêm raw mới |

Không cần quan tâm các tham số khác, hệ thống đã để mặc định.

### Các Bước Crawl

Bước 1: kiểm tra trước.

```powershell
python data_pipeline\src\data_scraping\google_maps_reviews.py crawl --start-row 1 --limit 5 --reviews-per-place 200 --dry-run
```

Bước 2: crawl thật.

```powershell
python data_pipeline\src\data_scraping\google_maps_reviews.py crawl --start-row 1 --limit 5 --reviews-per-place 200
```

Bước 3: process raw thành output sạch.

```powershell
python data_pipeline\src\data_scraping\google_maps_reviews.py process --append
```

Ví dụ crawl đủ 50 địa điểm:

```powershell
python data_pipeline\src\data_scraping\google_maps_reviews.py crawl --start-row 1 --limit 50 --reviews-per-place 200
python data_pipeline\src\data_scraping\google_maps_reviews.py process --append
```

### Output Và Cách Kiểm Tra

Raw data:

```text
data_pipeline/data/raw/google_maps/reviews/
```

Output sạch:

```text
data_pipeline/data/outputs/google_maps/google_maps_reviews_output.csv
```

Kiểm tra nhanh số dòng:

```powershell
(Import-Csv data_pipeline\data\outputs\google_maps\google_maps_reviews_output.csv).Count
```

Kiểm tra bằng Excel/VS Code: mở file `google_maps_reviews_output.csv`, xem có cột `place_id`, `review_text`, `rating` hay không.

### Lưu Ý Append Và Process

- Crawl Google Maps tạo raw trong `data_pipeline/data/raw/google_maps/reviews/`.
- Process có thể chạy lại nhiều lần, không tốn credit.
- Khi đã có output cũ và muốn cộng thêm batch mới, dùng `process --append`.

## 2. Facebook

Facebook đã được đơn giản hóa thành một lệnh chính. Người crawl chỉ cần đưa list địa điểm hoặc chọn dòng trong master file.

Script:

```text
data_pipeline/src/data_scraping/facebook.py
```

Lệnh Facebook tự động chạy 3 tầng:

```text
source -> post -> comment
```

Trong đó:

| Tầng | Hệ thống làm gì |
|---|---|
| source | Tìm link Facebook liên quan tới địa điểm |
| post | Lấy bài viết từ source nếu Facebook cho phép |
| comment | Lấy comment từ post/video/photo tìm được |

### Tham Số Cần Dùng

| Tham số | Ý nghĩa dễ hiểu | Khi nào dùng |
|---|---|---|
| `--place-ids` | Danh sách mã địa điểm cần crawl | Cách để người crawl đưa list địa điểm rõ ràng |
| `--start-row` | Bắt đầu từ dòng thứ mấy trong file master | Khi chia việc theo batch |
| `--limit` | Số địa điểm cần crawl từ `--start-row` | Ví dụ `--start-row 1 --limit 5` |
| `--append` | Gộp kết quả mới vào output cũ | Nên dùng khi crawl thật |
| `--dry-run` | Xem trước pipeline, không tốn credit | Nên chạy trước khi crawl thật |
| `--limit-sources-per-place` | Mỗi địa điểm dùng tối đa bao nhiêu source để crawl post | Nên dùng `2` |
| `--limit-posts-per-place` | Mỗi địa điểm crawl comment từ tối đa bao nhiêu post/video/photo | Nên dùng `3` |
| `--comments-limit` | Số comment tối đa mỗi post/video/photo | Test dùng `20`, crawl thật dùng `100` |

Không cần nhắc tới các tham số nâng cao khác trong lúc crawl bình thường.

### Các Bước Crawl

Bước 1: test trước cho 2 địa điểm.

```powershell
python data_pipeline\src\data_scraping\facebook.py crawl --place-ids dalat_001,dalat_002 --dry-run
```

Bước 2: crawl thật theo list địa điểm.

```powershell
python data_pipeline\src\data_scraping\facebook.py crawl --place-ids dalat_001,dalat_002,dalat_003 --append --limit-sources-per-place 2 --limit-posts-per-place 3 --comments-limit 100
```

Bước 3: hoặc crawl theo dòng trong master file.

```powershell
python data_pipeline\src\data_scraping\facebook.py crawl --start-row 1 --limit 5 --append --limit-sources-per-place 2 --limit-posts-per-place 3 --comments-limit 100
```

Khi chạy, terminal sẽ hiện log dạng này:

```text
[FACEBOOK SOURCES] Places: dalat_001:10, dalat_002:9
[FACEBOOK COMMENTS] Places: dalat_001:1, dalat_002:1
```

Nghĩa là mỗi địa điểm đã có dữ liệu ở từng tầng. Nếu thiếu một `place_id`, có thể lần crawl đó Google/Facebook không trả source cho địa điểm đó.

### Output Và Cách Kiểm Tra

Raw data:

```text
data_pipeline/data/raw/facebook/sources/
data_pipeline/data/raw/facebook/posts/
data_pipeline/data/raw/facebook/comments/
```

Output sạch:

```text
data_pipeline/data/outputs/facebook/facebook_sources.csv
data_pipeline/data/outputs/facebook/facebook_post_seeds.csv
data_pipeline/data/outputs/facebook/facebook_post_rejections.csv
data_pipeline/data/outputs/facebook/facebook_comments_output.csv
```

File quan trọng nhất:

```text
data_pipeline/data/outputs/facebook/facebook_comments_output.csv
```

Kiểm tra nhanh số dòng:

```powershell
(Import-Csv data_pipeline\data\outputs\facebook\facebook_comments_output.csv).Count
```

Kiểm tra mỗi địa điểm có bao nhiêu comment:

```powershell
Import-Csv data_pipeline\data\outputs\facebook\facebook_comments_output.csv | Group-Object place_id | Select-Object Name,Count
```

Nếu comment ít, kiểm tra source trước:

```powershell
Import-Csv data_pipeline\data\outputs\facebook\facebook_sources.csv | Group-Object place_id | Select-Object Name,Count
```

### Lưu Ý Append Và Process

- Với Facebook, người crawl nên dùng lệnh `crawl` duy nhất. Lệnh này tự crawl và tự process.
- Khi crawl thật, gần như luôn thêm `--append`.
- Nếu quên `--append`, output có thể bị ghi lại theo batch mới.
- `facebook_post_seeds.csv` có thể ít hoặc rỗng vì Facebook page có thể chặn public post. Đây không nhất thiết là lỗi; nếu `facebook_comments_output.csv` vẫn có data thì pipeline vẫn đúng.
- Nếu chỉ test, dùng `--comments-limit 20` để tiết kiệm. Khi crawl thật, dùng `--comments-limit 100`.

## 3. TikTok

TikTok có 2 tầng:

```text
video seed -> comment
```

Seed video là video được chọn làm nguồn để crawl comment. Không phải video nào tìm thấy cũng được giữ lại. Process video sẽ lọc theo độ liên quan và số comment.

Script:

```text
data_pipeline/src/data_scraping/tiktok.py
```

### Tham Số Cần Dùng

| Tham số | Ý nghĩa dễ hiểu | Khi nào dùng |
|---|---|---|
| `--start-row` | Bắt đầu từ dòng thứ mấy trong file master | Khi chia việc theo batch |
| `--limit` | Số địa điểm cần crawl video | Thường dùng `5` hoặc `10` |
| `--dry-run` | Kiểm tra lệnh, không crawl thật | Nên chạy trước |
| `--latest` | Process file raw mới nhất vừa crawl | Dùng sau mỗi lần crawl |
| `--append-output` | Gộp output mới vào output cũ | Dùng khi crawl thêm batch mới |
| `--min-video-comments` | Video phải có ít nhất bao nhiêu comment mới được giữ | Nếu ít seed thì hạ xuống `5`; nếu nhiều seed rác thì tăng lên `15` |
| `--min-relevance-score` | Điểm liên quan tới địa điểm | Thường dùng `3.0` đến `3.5` |
| `--max-seed-videos-per-query` | Mỗi câu tìm kiếm giữ tối đa bao nhiêu video | Thường dùng `3` |
| `--place-ids` | Chỉ crawl comment cho các địa điểm này | Nên dùng để không crawl nhầm địa điểm cũ |
| `--limit-videos` | Chỉ crawl comment từ một số video đầu tiên | Dùng khi test |

Không cần nhắc tới các tham số khác trong lúc crawl bình thường.

### Các Bước Crawl

Bước 1: test crawl video.

```powershell
python data_pipeline\src\data_scraping\tiktok.py crawl-videos --start-row 1 --limit 5 --dry-run
```

Bước 2: crawl video raw.

```powershell
python data_pipeline\src\data_scraping\tiktok.py crawl-videos --start-row 1 --limit 5
```

Bước 3: process video thành seed.

```powershell
python data_pipeline\src\data_scraping\tiktok.py process-videos --latest --append-output --min-video-comments 10 --min-relevance-score 3.0 --max-seed-videos-per-query 3
```

Bước 4: crawl comment từ seed video. Nên truyền đúng `place_id` của batch vừa crawl.

```powershell
python data_pipeline\src\data_scraping\tiktok.py crawl-comments --place-ids dalat_001,dalat_002,dalat_003,dalat_004,dalat_005
```

Bước 5: process comment.

```powershell
python data_pipeline\src\data_scraping\tiktok.py process-comments --latest --append-output
```

Test nhỏ cho 1 địa điểm và 1 video:

```powershell
python data_pipeline\src\data_scraping\tiktok.py crawl-comments --place-ids dalat_001 --limit-videos 1 --dry-run
python data_pipeline\src\data_scraping\tiktok.py crawl-comments --place-ids dalat_001 --limit-videos 1
python data_pipeline\src\data_scraping\tiktok.py process-comments --latest --append-output
```

### Output Và Cách Kiểm Tra

Raw data:

```text
data_pipeline/data/raw/tiktok/videos/
data_pipeline/data/raw/tiktok/comments/
```

Output sạch:

```text
data_pipeline/data/outputs/tiktok/tiktok_video_seeds.csv
data_pipeline/data/outputs/tiktok/tiktok_video_rejections.csv
data_pipeline/data/outputs/tiktok/tiktok_comments_output.csv
data_pipeline/data/outputs/tiktok/tiktok_comment_rejections.csv
```

File quan trọng nhất:

```text
data_pipeline/data/outputs/tiktok/tiktok_comments_output.csv
```

Kiểm tra số seed video:

```powershell
(Import-Csv data_pipeline\data\outputs\tiktok\tiktok_video_seeds.csv).Count
```

Kiểm tra comment theo địa điểm:

```powershell
Import-Csv data_pipeline\data\outputs\tiktok\tiktok_comments_output.csv | Group-Object place_id | Select-Object Name,Count
```

Kiểm tra video bị loại:

```text
data_pipeline/data/outputs/tiktok/tiktok_video_rejections.csv
```

### Lưu Ý Append Và Process

- TikTok cần process video trước để tạo `tiktok_video_seeds.csv`, sau đó mới crawl comment.
- Khi crawl thêm batch mới, process video và process comment nên có `--append-output`.
- Khi crawl comment, nên luôn dùng `--place-ids` của batch hiện tại để không crawl lại seed của địa điểm cũ.
- Nếu seed quá ít, hạ `--min-video-comments` xuống `5` hoặc hạ `--min-relevance-score` xuống `3.0`.
- Nếu seed quá nhiều và bị nhiễu, tăng `--min-video-comments` lên `15` hoặc `20`, và tăng `--min-relevance-score` lên `3.5` hoặc `4.0`.

## Kiểm Tra Sau Khi Crawl Xong

Kiểm tra nhanh các output chính:

```powershell
(Import-Csv data_pipeline\data\outputs\google_maps\google_maps_reviews_output.csv).Count
(Import-Csv data_pipeline\data\outputs\facebook\facebook_comments_output.csv).Count
(Import-Csv data_pipeline\data\outputs\tiktok\tiktok_comments_output.csv).Count
```

Kiểm tra mỗi địa điểm có bao nhiêu dòng:

```powershell
Import-Csv data_pipeline\data\outputs\facebook\facebook_comments_output.csv | Group-Object place_id | Select-Object Name,Count
Import-Csv data_pipeline\data\outputs\tiktok\tiktok_comments_output.csv | Group-Object place_id | Select-Object Name,Count
```

Sau khi crawl xong 3 nền tảng, chạy pipeline xử lý tổng hợp:

```powershell
python data_pipeline\src\data_processing\build_cross_platform_dataset.py
python data_pipeline\src\data_processing\normalize_percent_outputs.py
```

