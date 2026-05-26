# DaLat Authentrail

Nền tảng đánh giá độ tin cậy địa điểm Đà Lạt — tổng hợp dữ liệu từ Google Maps, Facebook và TikTok, hiển thị Trust Score và hỗ trợ hỏi đáp cộng đồng thực tế.

## Kiến trúc

```
dalat_authentrail/
├── apps/
│   ├── api/          Hono backend — REST API + Socket.io (Node.js)
│   └── web/          Next.js 16 — App Router, Tailwind v4
├── packages/
│   └── types/        Shared TypeScript types
├── data_pipeline/    Python pipeline — crawl, xử lý, tính Trust Score
│   ├── src/
│   │   ├── data_scraping/     Crawlers (Google Maps, Facebook, TikTok)
│   │   └── data_processing/   Cleaning, NLP, trust scoring
│   └── data/
│       ├── raw/               Dữ liệu thô (gitignored)
│       ├── interim/           Trung gian (gitignored)
│       ├── processed/         CSV curated (một phần được commit)
│       └── outputs/           Output cuối — các file được commit
└── docs/             Thiết kế hệ thống, DFD
```

## Tech Stack

| Layer | Công nghệ |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS v4, NextAuth v4 |
| Backend | Hono, Node.js, Socket.io |
| Database | PostgreSQL + Prisma ORM |
| Cache / Realtime | Redis + Socket.io |
| Auth | Google OAuth via NextAuth |
| Pipeline | Python, Apify, pandas, scikit-learn |
| Deploy | Vercel (web) + Railway (API + DB + Redis) |

## Yêu cầu môi trường local

- Node.js ≥ 20
- pnpm ≥ 9
- PostgreSQL 18
- Redis (tuỳ chọn — chỉ cần cho real-time)
- Python ≥ 3.11 + pip (chỉ cho data pipeline)

## Khởi động local

```powershell
# 1. Cài dependencies
pnpm install

# 2. Tạo database (PostgreSQL phải đang chạy)
pnpm db:push

# 3. Seed dữ liệu ban đầu
pnpm db:seed

# 4. Chạy cả api và web
pnpm dev
```

API chạy tại `http://localhost:4000` — Web tại `http://localhost:3000`.

### Biến môi trường

**`apps/api/.env`** (copy từ `.env.example`):
```
DATABASE_URL=postgresql://postgres:PASSWORD@localhost:5432/dalat_authentrail
REDIS_URL=redis://localhost:6379
PORT=4000
NODE_ENV=development
NEXTAUTH_SECRET=dev-secret-change-in-production
CORS_ORIGIN=http://localhost:3000
```

**`apps/web/.env.local`** (copy từ `.env.example`):
```
NEXT_PUBLIC_API_URL=http://localhost:4000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=dev-secret-change-in-production
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

## API Endpoints

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/places` | Tìm kiếm địa điểm (hỗ trợ q, category, risk_level, page) |
| GET | `/api/places/:id` | Chi tiết địa điểm |
| GET | `/api/places/:id/reviews` | Danh sách review |
| GET | `/api/places/:id/risk` | Risk score chi tiết |
| GET | `/api/questions?placeId=` | Câu hỏi của địa điểm / toàn bộ feed |
| POST | `/api/questions` | Tạo câu hỏi mới (yêu cầu auth) |
| GET | `/api/answers?questionId=` | Câu trả lời của một câu hỏi |
| POST | `/api/answers/:questionId` | Đăng câu trả lời (yêu cầu auth) |
| POST | `/api/answers/:id/vote` | Like / dislike câu trả lời (yêu cầu auth) |

Auth qua header: `X-User-Id`, `X-User-Email`, `X-User-Name` (do web app inject từ NextAuth session).

## Socket.io Events

Kết nối tại `ws://localhost:4000`. Client emit `join:place <placeId>` để nhận real-time updates cho một địa điểm.

| Event | Chiều | Dữ liệu |
|---|---|---|
| `join:place` | Client → Server | `placeId: string` |
| `leave:place` | Client → Server | `placeId: string` |
| `question:new` | Server → Client | `Question` object |
| `answer:new` | Server → Client | `{ questionId, answer }` |

## Data Pipeline

```powershell
# Crawl Google Maps
python data_pipeline/src/data_scraping/google_maps.py

# Crawl TikTok từng batch
python data_pipeline/src/data_scraping/tiktok.py crawl-videos --start-row 1 --limit 50

# Xử lý và tính trust score
python data_pipeline/src/data_processing/trust_score.py

# Import kết quả vào PostgreSQL
pnpm db:seed
```

## Deploy

- **API + DB + Redis** → Railway (xem `apps/api/.env.example`)
- **Web** → Vercel (Root Directory: `apps/web`, xem `apps/web/.env.example`)
- **Google OAuth** → Thêm redirect URI production vào Google Cloud Console

## Cấu trúc Trust Score

Trust Score được tính qua 3 lớp:

1. **Layer 1** — Quality filtering (loại bỏ review spam, bot)
2. **Layer 2** — Sentiment & topic analysis (phân tích cảm xúc, chủ đề)
3. **Layer 3** — Cross-platform risk scoring (so sánh chéo Google Maps vs Social)

Risk Level: `low` (≤ 0.35) / `medium` (0.35–0.65) / `high` (> 0.65)
