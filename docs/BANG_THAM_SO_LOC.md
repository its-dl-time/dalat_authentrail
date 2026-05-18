# Bảng Tham Số Lọc Dữ Liệu

Tài liệu này tóm tắt các ngưỡng lọc comment, review, post, video trong pipeline.

## Google Places Master

| File | Tham số | Mặc định | Dùng để lọc | Ghi chú |
|---|---:|---:|---|---|
| `clean_places.py` | `MIN_REVIEWS` | `100` | Địa điểm có ít nhất 100 review | Giảm nếu thiếu địa điểm |
| `clean_places.py` | `TOP_N` | `50` | Chọn top N địa điểm sau khi chấm `data_score` | Tăng nếu muốn master lớn hơn |

## Google Maps Reviews

| File | Tham số | Mặc định | Tác dụng | Ghi chú |
|---|---:|---:|---|---|
| `google_maps_reviews.py` | `REVIEWS_PER_PLACE` | `50` | Số review tối đa mỗi địa điểm | Không lọc chất lượng text |
| `google_maps_reviews.py` | `BATCH_SIZE` | `5` | Số địa điểm mỗi actor run | Giảm nếu mapping không chắc |

Google Maps hiện chủ yếu chuẩn hóa field và dedupe theo `id`, chưa lọc review theo độ dài/chất lượng.

## TikTok Video

| File | Tham số | Mặc định | Điều kiện lọc | Bị loại với lý do |
|---|---:|---:|---|---|
| `tiktok.py` | `MIN_VIDEO_COMMENTS` | `20` | Video phải có ít nhất 20 comment | `too_few_comments_*` |
| `tiktok.py` | `MIN_RELEVANCE_SCORE` | `3.5` | Video phải đạt điểm liên quan từ 3.5 | `low_relevance_*` |
| `tiktok.py` | `MAX_SEED_VIDEOS_PER_QUERY` | `1` | Giữ tối đa 1 video/query | Không phải rejection, chỉ cắt top |
| `tiktok.py` | `MAX_SEED_VIDEOS_TOTAL_PER_PLACE` | `10` | Giới hạn seed video mỗi địa điểm | Không phải rejection, chỉ quota |

Điểm `video_relevance_score`:

| Tín hiệu | Điểm |
|---|---:|
| Caption chứa tên địa điểm | `+4` |
| Caption chứa Đà Lạt/dalat/da lat | `+2` |
| Match token query | tối đa `+3` nếu đã match place, tối đa `+2` nếu chưa |
| Comment count từ 50/100 | `+0.5` / `+1` |
| Views từ 5k/10k | `+0.25` / `+0.5` |
| Likes từ 150/300 | `+0.25` / `+0.5` |
| Caption quá ngắn `<20` ký tự | `-1` |

## TikTok Comment

| File | Tham số | Mặc định | Điều kiện lọc | Bị loại với lý do |
|---|---:|---:|---|---|
| `tiktok.py` | `COMMENTS_PER_VIDEO` | `20` | Số comment crawl mỗi video | Không phải filter |
| `tiktok.py` | `MAX_REPLIES_PER_COMMENT` | `1` | Số reply tối đa mỗi comment | Không phải filter |
| `tiktok.py` | `MIN_COMMENT_WORDS` | `10` | Comment hữu ích nên đủ 10 từ | Dùng trong `is_useful_comment` |
| `tiktok.py` | `MIN_USEFUL_TERMS_MATCH` | `2` | Cần từ 2 tín hiệu review trở lên | `is_useful_comment=False` |
| `tiktok.py` | quality threshold | `0.2` | Comment phải có quality >= 0.2 | `low_quality_*` |
| `tiktok.py` | emoji ratio spam | `>0.5` khi text rất ngắn | Emoji-only/emoji-heavy | `likely_spam` |

Điểm `comment_quality_score`:

| Tín hiệu | Điểm |
|---|---:|
| Độ dài 40-500 ký tự | `+0.4` |
| Độ dài 20-39 ký tự | `+0.2` |
| Độ dài >500 ký tự | `+0.3` |
| Emoji ratio `<0.1` | `+0.3` |
| Emoji ratio `<0.3` | `+0.15` |
| Ngôn ngữ `vi` | `+0.2` |
| Ngôn ngữ `mixed` | `+0.1` |
| Likely spam | `-0.3` |

## Facebook Source

| File | Tham số | Mặc định | Điều kiện lọc | Ghi chú |
|---|---:|---:|---|---|
| `01_facebook_gg.py` | `MIN_SOURCE_SCORE` | `4` | Source phải đạt ít nhất 4 điểm | Source thấp hơn bị bỏ |
| `01_facebook_gg.py` | `QUERIES_PER_PLACE` | `2` | Số query Google/place | Tăng nếu thiếu source |
| `01_facebook_gg.py` | `RESULTS_PER_PAGE` | `10` | Số kết quả Google/query | Tăng sẽ tốn hơn |

Điểm `source_score`:

| Tín hiệu | Điểm |
|---|---:|
| URL là Facebook | `+2` |
| Nội dung chứa tên địa điểm | `+3` |
| Nội dung chứa Đà Lạt/dalat/da lat | `+2` |
| Source là page/profile | `+2` |
| Source là post/reel/video | `+2` |
| Source là group | `+1` |
| URL xấu như login/sharer/privacy/l.php | `-6` |

## Facebook Post

| File | Tham số | Mặc định | Điều kiện lọc | Bị loại với lý do |
|---|---:|---:|---|---|
| `02_facebook_posts.py` | `RESULTS_LIMIT_PER_SOURCE` | `30` | Số post lấy từ mỗi source | Không phải filter |
| `02_facebook_posts.py` | `ONLY_POSTS_NEWER_THAN` | `12 months` | Chỉ lấy post mới hơn 12 tháng | Theo actor |
| `02_facebook_posts.py` | `MIN_POST_COMMENTS` | `5` | Post phải có ít nhất 5 comment | `too_few_comments` |
| `02_facebook_posts.py` | `MIN_POST_RELEVANCE_SCORE` | `3.5` | Post phải liên quan đủ | `low_relevance` |
| `02_facebook_posts.py` | text length | `>=10` ký tự normalized | Post phải có text đủ dài | `too_short_text` |

Điểm `post_relevance_score`:

| Tín hiệu | Điểm |
|---|---:|
| Post text chứa tên địa điểm | `+4` |
| Post text chứa Đà Lạt/dalat/da lat | `+2` |
| Source title/snippet chứa tên địa điểm | `+1.5` |
| Từ ngữ review/check-in/ngon/đẹp/giá... | tối đa `+2` |
| Text quảng cáo/tuyển dụng/sale/inbox/voucher... | `-2.5` |

## Facebook Comment

| File | Tham số | Mặc định | Điều kiện lọc | Bị loại với lý do |
|---|---:|---:|---|---|
| `03_facebook_comments.py` | `COMMENTS_LIMIT_PER_POST` | `100` | Số comment tối đa mỗi post | Không phải filter |
| `03_facebook_comments.py` | `INCLUDE_NESTED_COMMENTS` | `True` | Lấy cả reply nested | Theo actor |
| `03_facebook_comments.py` | `MIN_COMMENT_WORDS` | `5` | Comment phải có ít nhất 5 từ | `too_short` |
| `03_facebook_comments.py` | quality threshold | `0.2` | Hữu ích nếu quality >= 0.2 và có tín hiệu review | `no_review_signal` |
| `03_facebook_comments.py` | spam link | Có `http` hoặc `www` | Loại comment có link | `likely_spam` |
| `03_facebook_comments.py` | owner/page reply | Author trùng/gần giống post author | Loại reply của page | `owner_or_page_reply` |
| `03_facebook_comments.py` | greeting/page pattern | Cảm ơn, inbox shop, bên em... | Loại phản hồi page/shop | `greeting_or_page_reply` |

Điểm `comment_quality_score` Facebook:

| Tín hiệu | Điểm |
|---|---:|
| Độ dài 40-500 ký tự | `+0.4` |
| Độ dài 20-39 ký tự | `+0.25` |
| Độ dài >500 ký tự | `+0.3` |
| Emoji ratio `<0.1` | `+0.3` |
| Emoji ratio `<0.3` | `+0.15` |
| Ngôn ngữ `vi` | `+0.2` |
| Ngôn ngữ `mixed` | `+0.1` |
| Ngôn ngữ `en` | `+0.05` |
| Likely spam | `-0.3` |

## Gợi Ý Chỉnh Ngưỡng

| Triệu chứng | Cách chỉnh |
|---|---|
| Quá ít video/post seed | Giảm `MIN_RELEVANCE_SCORE` hoặc `MIN_POST_RELEVANCE_SCORE` nhẹ, ví dụ `3.5 -> 3.0` |
| Quá nhiều comment rác | Tăng `MIN_COMMENT_WORDS`, tăng quality threshold, thêm junk terms |
| Thiếu comment hữu ích | Tăng `COMMENTS_PER_VIDEO` hoặc `COMMENTS_LIMIT_PER_POST` |
| Facebook map sai địa điểm | Giữ `SOURCE_BATCH_SIZE = 1`, `comments-batch-size = 1` |
| Tốn credit | Giảm `--limit`, `RESULTS_PER_PAGE`, `COMMENTS_PER_VIDEO`, `COMMENTS_LIMIT_PER_POST` |
