# Handoff Chuẩn Hóa Dữ Liệu Cross-Platform

Tài liệu này tóm tắt phần xử lý dữ liệu đã làm để gom dữ liệu từ Google Maps, TikTok và Facebook về cùng một cấu trúc, sau đó tạo bộ dữ liệu so sánh chéo theo từng địa điểm.

Mục tiêu hiện tại là tạo bản MVP dễ kiểm tra, dễ chạy lại, chưa dùng AI/LLM phức tạp. Output chính là `risk_score` cho từng địa điểm, kèm rating Google Maps để tham khảo.

## 1. Dữ liệu đầu vào

Pipeline đang dùng 4 file chính:

| File | Vai trò |
|---|---|
| `data/processed/places_master_top50.csv` | File master địa điểm. Đây là nơi chứa `place_id`, tên địa điểm, danh mục, địa chỉ, tọa độ, rating tổng Google Maps. |
| `data/outputs/google_maps/google_maps_reviews_output.csv` | Review Google Maps đã crawl. Có nội dung review, rating sao, người review, số like/helpful, Local Guide. |
| `data/outputs/tiktok/tiktok_comments_output.csv` | Comment TikTok đã crawl từ các video liên quan địa điểm. Có nội dung comment, like comment, thông tin video, quality score. |
| `data/outputs/facebook/facebook_comments_output.csv` | Comment Facebook đã crawl từ post/source liên quan địa điểm. Có nội dung comment, like comment, post gốc, quality score, reject reason. |

`place_id` là khóa chính để nối dữ liệu giữa các nền tảng. Ví dụ: `dalat_002`, `dalat_003`, `dalat_004`.

## 2. Những gì đã thực hiện

Đã tạo script:

```text
src/innostar/data_processing/build_cross_platform_dataset.py
```

Script này làm các bước sau:

1. Đọc file master địa điểm và 3 file output crawl.
2. Tìm các địa điểm có đủ cả 3 nền tảng Google Maps, TikTok, Facebook.
3. Với dữ liệu hiện tại, MVP chỉ giữ:
   - `dalat_002`
   - `dalat_003`
   - `dalat_004`
4. Xóa dòng trùng theo cột `id` trong từng file nguồn.
5. Chuẩn hóa các cột chung về một schema thống nhất.
6. Giữ các cột riêng từng nền tảng trong file riêng.
7. Chấm sentiment/topic/risk bằng rule-based đơn giản.
8. Tổng hợp dữ liệu theo `place_id + platform`.
9. Tính `risk_score` cuối cùng cho từng địa điểm.

## 3. Pipeline hiện tại

### Bước 1: Load và lọc địa điểm đủ nền tảng

Script đọc dữ liệu từ 3 nền tảng, sau đó chỉ giữ địa điểm xuất hiện ở cả Google Maps, TikTok và Facebook.

Lý do: so sánh chéo chỉ có ý nghĩa khi một địa điểm có đủ dữ liệu từ nhiều nguồn.

### Bước 2: Chuẩn hóa dữ liệu chung

Các nguồn có tên cột khác nhau, nên script đưa về cùng một bộ cột.

Ví dụ:

| Ý nghĩa | Google Maps | TikTok | Facebook | Cột chuẩn hóa |
|---|---|---|---|---|
| Nội dung | `review_text` | `comment_text` | `comment_text` | `content_text` |
| Thời gian đăng | `published_at` | `comment_created_at` | `comment_created_at` | `content_created_at` |
| Tương tác | `likes_count` | `comment_likes` | `comment_likes` | `engagement_count` |
| Người viết | `reviewer_id/name` | `comment_author` | `comment_author/url` | `author_id_or_name` |

File kết quả:

```text
data/processed/cross_platform/normalized_common_records.csv
```

Đây là file quan trọng nhất nếu muốn phân tích tất cả review/comment chung một chỗ.

### Bước 3: Giữ feature riêng từng nền tảng

Không phải cột nào cũng so sánh được giữa các nền tảng.

Ví dụ Google Maps có rating sao, TikTok có view/like video, Facebook có post gốc và reject reason. Những cột này được giữ riêng để không làm rối file chung.

Các file kết quả:

```text
data/processed/cross_platform/platform_google_maps_features.csv
data/processed/cross_platform/platform_tiktok_features.csv
data/processed/cross_platform/platform_facebook_features.csv
```

### Bước 4: Rule-based NLP MVP

Pipeline hiện tại chưa dùng model AI. Script đang dùng rule đơn giản để tạo các feature:

| Feature | Ý nghĩa |
|---|---|
| `sentiment_score` | Điểm cảm xúc từ `-1` đến `1`. Âm là tiêu cực, dương là tích cực. |
| `service_score` | Nội dung có nhắc đến phục vụ/nhân viên/thái độ không. |
| `price_score` | Nội dung có nhắc đến giá/đắt/rẻ không. |
| `scenery_score` | Nội dung có nhắc đến view/cảnh/check-in không. |
| `crowded_score` | Nội dung có nhắc đến đông/chờ lâu/xếp hàng không. |
| `food_drink_score` | Nội dung có nhắc đến món ăn/nước/cafe không. |
| `cleanliness_score` | Nội dung có nhắc đến sạch/bẩn/vệ sinh không. |
| `location_score` | Nội dung có nhắc đến đường đi/vị trí/gửi xe không. |
| `risk_flags` | Các cờ rủi ro như text rỗng, quá ngắn, nhiều emoji, spam, quảng cáo. |

Lưu ý: đây mới là bản MVP để có pipeline chạy được. Kết quả NLP chưa phải kết quả cuối cùng để dùng sản phẩm thật.

### Bước 5: Tổng hợp theo địa điểm và nền tảng

Sau khi chuẩn hóa từng dòng, script gom dữ liệu theo từng cặp:

```text
place_id + platform
```

Ví dụ:

```text
dalat_002 + google_maps
dalat_002 + tiktok
dalat_002 + facebook
```

File kết quả:

```text
data/processed/cross_platform/place_platform_summary.csv
```

File này cho biết mỗi nền tảng đang nói gì về từng địa điểm:

- Có bao nhiêu review/comment.
- Tỷ lệ nội dung hữu ích.
- Sentiment trung bình.
- Tỷ lệ nội dung tiêu cực.
- Tỷ lệ record bị gắn cờ rủi ro.
- Điểm topic trung bình.
- Với Google Maps có thêm rating trung bình từ review và rating master.

### Bước 6: Tính risk score theo địa điểm

Script tạo file cuối:

```text
data/processed/cross_platform/place_cross_platform_risk.csv
```

Mỗi dòng là một địa điểm.

Các cột chính:

| Cột | Ý nghĩa |
|---|---|
| `place_id` | ID địa điểm. |
| `place_name` | Tên địa điểm. |
| `google_maps_rating` | Rating Google Maps từ master file. |
| `risk_score` | Điểm rủi ro từ `0` đến `1`. Càng cao càng rủi ro. |
| `risk_level` | Mức rủi ro: `low`, `medium`, `high`. |
| `data_quality_risk` | Rủi ro do dữ liệu nhiều text ngắn, spam, reject, low quality. |
| `sentiment_gap` | Độ lệch cảm xúc giữa các nền tảng. |
| `negative_social_vs_maps_gap` | Social tiêu cực trong khi Google Maps vẫn cao. |
| `topic_gap` | Chủ đề bị lệch giữa các nền tảng. |
| `engagement_gap` | Tương tác lệch giữa các nền tảng. |
| `coverage_risk` | Rủi ro do tỷ lệ nội dung hữu ích thấp. |

Thang điểm:

| Risk score | Risk level | Diễn giải |
|---:|---|---|
| `< 0.33` | `low` | Ít dấu hiệu rủi ro. |
| `0.33 - < 0.66` | `medium` | Có dấu hiệu cần kiểm tra thêm. |
| `>= 0.66` | `high` | Rủi ro cao, nên xem kỹ dữ liệu gốc. |

## 4. Hướng dẫn chạy cho người chưa biết code

### Bước 1: Mở terminal

Mở PowerShell hoặc terminal trong thư mục project:

```powershell
cd D:\INNOSTAR
```

### Bước 2: Cài thư viện nếu chưa cài

Chỉ cần chạy một lần:

```powershell
pip install -r requirements.txt
```

Nếu đang dùng môi trường ảo `.venv`, kích hoạt trước:

```powershell
.\.venv\Scripts\activate
```

Sau đó chạy lại:

```powershell
pip install -r requirements.txt
```

### Bước 3: Chạy pipeline chuẩn hóa

Chạy lệnh:

```powershell
python src\innostar\data_processing\build_cross_platform_dataset.py
```

Nếu chạy thành công, terminal sẽ hiện kiểu như:

```text
Cross-platform dataset built.
Complete places: dalat_002, dalat_003, dalat_004
Normalized records: 819
Place-platform summary rows: 9
Risk rows: 3
```

### Bước 4: Xem kết quả

Mở thư mục:

```text
data/processed/cross_platform/
```

File nên xem đầu tiên:

```text
place_cross_platform_risk.csv
```

File này là kết quả cuối theo từng địa điểm.

Nếu muốn xem dữ liệu chi tiết từng comment/review sau chuẩn hóa, mở:

```text
normalized_common_records.csv
```

## 5. Các file output cụ thể làm gì

| File | Dùng để làm gì |
|---|---|
| `normalized_common_records.csv` | Dữ liệu chung đã chuẩn hóa từ cả 3 nền tảng, mỗi dòng là một review/comment. |
| `platform_google_maps_features.csv` | Feature riêng của Google Maps như rating, Local Guide, reviewer review count, owner response. |
| `platform_tiktok_features.csv` | Feature riêng của TikTok như video URL, caption, view, like video, comment count. |
| `platform_facebook_features.csv` | Feature riêng của Facebook như source URL, post URL, post relevance, comment depth, reject reason. |
| `place_platform_summary.csv` | Bảng tổng hợp theo từng địa điểm và từng nền tảng. |
| `place_cross_platform_risk.csv` | Bảng risk score cuối cùng theo từng địa điểm. |

## 6. Những việc cần làm tiếp theo

Pipeline hiện tại đã chạy được end-to-end, nhưng để đạt đúng mục tiêu ban đầu thì cần tối ưu thêm các phần sau.

### 6.1. Nâng cấp NLP sentiment

Hiện tại sentiment đang dựa trên từ khóa đơn giản. Cần nâng cấp để hiểu ngữ cảnh tốt hơn.

Ví dụ khó:

- "View đẹp nhưng phục vụ quá tệ"
- "Không tệ nha"
- "Quán này đông kinh khủng nhưng đáng thử"
- Comment dùng tiếng lóng, viết tắt, mỉa mai.

Hướng tối ưu:

1. Tạo tập dữ liệu mẫu đã gán nhãn thủ công.
2. Gán nhãn sentiment: tích cực, trung tính, tiêu cực, mixed.
3. Dùng model NLP/LLM để phân loại.
4. So sánh kết quả model với rule hiện tại.

### 6.2. Nâng cấp topic extraction

Topic hiện tại cũng đang dựa trên từ khóa. Nên nâng cấp để bắt được ý nghĩa dù người dùng không dùng đúng từ khóa.

Ví dụ:

- "Nhân viên không thèm nhìn khách" nên thuộc topic service.
- "Ly này 80k hơi đau ví" nên thuộc topic price.
- "Đường vào hơi khó kiếm" nên thuộc topic location.

Hướng tối ưu:

1. Chốt taxonomy topic cố định.
2. Gán nhãn topic cho một tập comment/review mẫu.
3. Dùng embedding hoặc LLM để phân loại topic.
4. Cho phép một review/comment có nhiều topic cùng lúc.

### 6.3. Tách comment thật sự có giá trị review

TikTok/Facebook có nhiều comment không phải review thật, ví dụ:

- Tag bạn bè.
- Emoji.
- "Xin địa chỉ"
- "Đẹp quá"
- Comment đùa hoặc không liên quan.

Cần cải thiện `is_useful` để chỉ giữ nội dung có tín hiệu trải nghiệm thật.

Hướng tối ưu:

1. Tạo nhãn `useful_review`, `not_review`, `question`, `spam`, `owner_reply`.
2. Dùng model phân loại.
3. Khi tính risk, giảm trọng số những comment không phải review thật.

### 6.4. Tối ưu công thức risk score

Công thức hiện tại là MVP có trọng số thủ công.

Các thành phần đang dùng:

- `data_quality_risk`
- `sentiment_gap`
- `negative_social_vs_maps_gap`
- `topic_gap`
- `engagement_gap`
- `coverage_risk`

Cần tối ưu bằng cách:

1. Review thủ công một số địa điểm.
2. Xem risk score có hợp lý không.
3. Điều chỉnh trọng số.
4. Có thể tách risk thành nhiều loại:
   - Risk do seeding.
   - Risk do chất lượng dịch vụ.
   - Risk do dữ liệu thiếu.
   - Risk do lệch giữa các nền tảng.

### 6.5. Bổ sung dữ liệu thiếu nền tảng

Hiện MVP chỉ tính địa điểm có đủ 3 nền tảng.

Về sau nên xử lý cả địa điểm thiếu 1-2 nền tảng bằng `coverage_risk`, nhưng cần quy định rõ:

- Thiếu TikTok có bị phạt không?
- Thiếu Facebook có bị phạt không?
- Google Maps có phải nguồn bắt buộc không?
- Bao nhiêu review/comment là đủ tin cậy?

### 6.6. Thêm embedding similarity để phát hiện seeding

Trong plan ban đầu có phần phát hiện nội dung lặp, paraphrase, template spam.

Hiện tại chưa làm phần này.

Hướng tối ưu:

1. Tạo embedding cho từng review/comment.
2. So sánh độ giống nhau trong cùng một địa điểm.
3. Nếu nhiều nội dung rất giống nhau, tăng seeding risk.
4. So sánh theo cụm topic, không chỉ so từng câu.

### 6.7. Thêm kiểm thử tự động

Hiện đã kiểm tra thủ công sau khi chạy script.

Nên thêm test tự động để đảm bảo:

- Output luôn có đúng cột.
- Không mất `place_id`.
- `risk_score` luôn nằm trong `[0, 1]`.
- Chỉ địa điểm đủ nền tảng mới vào MVP output.
- Dữ liệu thiếu text/rating/engagement không làm pipeline lỗi.

## 7. Ghi chú về Git

Các file dữ liệu mẫu chính đã được mở trong `.gitignore` để có thể push lên git:

- `.env`
- `data/processed/places_master_top50.csv`
- `data/outputs/google_maps/google_maps_reviews_output.csv`
- `data/outputs/tiktok/tiktok_comments_output.csv`
- `data/outputs/facebook/facebook_comments_output.csv`
- `data/processed/cross_platform/*.csv`

Các thư mục vẫn nên bỏ qua:

- `.venv/`
- `__pycache__/`
- file raw Google Places lớn trong `data/raw/google_places/`
- model/cache/log tạm

Trước khi push, nên mở `.env` kiểm tra chắc chắn không còn API key thật.
