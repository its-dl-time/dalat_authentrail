/**
 * Seed script — populates DB from existing pipeline CSV files + mock places for dev/testing.
 *
 * Run:  pnpm db:seed
 *
 * Sources:
 *   - data_pipeline/data/processed/cross_platform/place_cross_platform_risk.csv
 *   - data_pipeline/data/processed/cross_platform/place_platform_summary.csv
 *   - data_pipeline/data/processed/cross_platform/normalized_common_records.csv
 *   - data_pipeline/data/processed/cross_platform/place_weighted_rating.csv
 * + mock place definitions below (extract from frontend.html)
 */

import { PrismaClient, Platform, RiskLevel, TrustLevel } from "@prisma/client";
import fs from "fs";
import path from "path";
import { parse } from "csv-parse/sync";

const prisma = new PrismaClient();

// ─── Paths ────────────────────────────────────────────────────────────────────

const CSV_DIR = path.resolve(__dirname, "../../../data_pipeline/data/processed/cross_platform");

function readCsv(filename: string): Record<string, string>[] {
  const content = fs.readFileSync(path.join(CSV_DIR, filename), { encoding: "utf-8" });
  return parse(content, { columns: true, skip_empty_lines: true, bom: true }) as Record<string, string>[];
}

function f(val: string | undefined, fallback = 0): number {
  const n = parseFloat(val ?? "");
  return isNaN(n) ? fallback : n;
}

// ─── Mock places (extracted from frontend.html — replace with real data after pipeline runs) ──

const MOCK_PLACES = [
  {
    id: "dalat_001",
    name: "Cà phê Tà Xùa Đà Lạt",
    category: "Quán cà phê",
    address: "20 Hoàng Diệu, Đà Lạt",
    lat: 11.9404,
    lng: 108.4582,
    googleMapsRating: 4.5,
    weightedRating: 4.4,
    riskScore: 0.18,
    riskLevel: RiskLevel.low,
  },
  {
    id: "dalat_003",
    name: "Nhà hàng Bích Đào",
    category: "Nhà hàng",
    address: "8 Lê Đại Hành, Đà Lạt",
    lat: 11.9453,
    lng: 108.4421,
    googleMapsRating: 4.1,
    weightedRating: 3.9,
    riskScore: 0.51,
    riskLevel: RiskLevel.medium,
  },
  {
    id: "dalat_004",
    name: "Vườn dâu tây Tây Sơn",
    category: "Địa điểm du lịch",
    address: "Tây Sơn, Đà Lạt",
    lat: 11.9721,
    lng: 108.4312,
    googleMapsRating: 4.3,
    weightedRating: 4.1,
    riskScore: 0.29,
    riskLevel: RiskLevel.low,
  },
  {
    id: "dalat_005",
    name: "Khách sạn Novotel Đà Lạt",
    category: "Lưu trú",
    address: "7 Trần Phú, Đà Lạt",
    lat: 11.9401,
    lng: 108.4429,
    googleMapsRating: 4.6,
    weightedRating: 4.5,
    riskScore: 0.12,
    riskLevel: RiskLevel.low,
  },
  {
    id: "dalat_006",
    name: "Chợ Đêm Đà Lạt",
    category: "Mua sắm",
    address: "Nguyễn Thị Minh Khai, Đà Lạt",
    lat: 11.9404,
    lng: 108.4432,
    googleMapsRating: 3.8,
    weightedRating: 3.5,
    riskScore: 0.65,
    riskLevel: RiskLevel.high,
  },
  {
    id: "dalat_007",
    name: "Đồi chè Cầu Đất",
    category: "Địa điểm du lịch",
    address: "Cầu Đất, Đà Lạt",
    lat: 11.8521,
    lng: 108.5031,
    googleMapsRating: 4.7,
    weightedRating: 4.6,
    riskScore: 0.08,
    riskLevel: RiskLevel.low,
  },
  {
    id: "dalat_008",
    name: "Quán ăn Dì Bảy",
    category: "Nhà hàng",
    address: "15 Phan Đình Phùng, Đà Lạt",
    lat: 11.9456,
    lng: 108.4398,
    googleMapsRating: 4.2,
    weightedRating: 4.0,
    riskScore: 0.34,
    riskLevel: RiskLevel.medium,
  },
  {
    id: "dalat_009",
    name: "The Dreamer Hotel",
    category: "Lưu trú",
    address: "34 Bùi Thị Xuân, Đà Lạt",
    lat: 11.9388,
    lng: 108.4502,
    googleMapsRating: 4.4,
    weightedRating: 4.2,
    riskScore: 0.22,
    riskLevel: RiskLevel.low,
  },
] as const;

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  console.log("🌱 Starting seed...");

  // ── 1. Load CSV data ──────────────────────────────────────────────────────

  const riskRows = readCsv("place_cross_platform_risk.csv");
  const summaryRows = readCsv("place_platform_summary.csv");
  const reviewRows = readCsv("normalized_common_records.csv");
  const weightedRows = readCsv("place_weighted_rating.csv");

  const weightedByPlace = Object.fromEntries(weightedRows.map((r) => [r.place_id, r]));

  // ── 2. Upsert real places from CSV ────────────────────────────────────────

  for (const row of riskRows) {
    const placeId = row.place_id;
    const weighted = weightedByPlace[placeId];

    await prisma.place.upsert({
      where: { id: placeId },
      create: {
        id: placeId,
        name: row.place_name,
        category: "Quán cà phê",          // TODO: add category to pipeline CSV
        lat: 11.9238342,                  // TODO: pull from seed DB / places_master
        lng: 108.4483607,
        googleMapsRating: f(row.google_maps_rating),
        weightedRating: f(weighted?.weighted_avg_rating),
      },
      update: {
        googleMapsRating: f(row.google_maps_rating),
        weightedRating: f(weighted?.weighted_avg_rating),
      },
    });

    // Risk score
    const level = (row.risk_level?.toLowerCase() ?? "medium") as RiskLevel;
    await prisma.riskScore.upsert({
      where: { placeId },
      create: {
        placeId,
        riskScore:               f(row.risk_score),
        riskLevel:               level,
        dataQualityRisk:         f(row.data_quality_risk),
        sentimentGap:            f(row.sentiment_gap),
        negativeSocialVsMapsGap: f(row.negative_social_vs_maps_gap),
        topicGap:                f(row.topic_gap),
        engagementGap:           f(row.engagement_gap),
        coverageRisk:            f(row.coverage_risk),
        googleMapsAvgSentiment:  f(row.google_maps_avg_sentiment),
        socialAvgSentiment:      f(row.social_avg_sentiment),
      },
      update: {
        riskScore:     f(row.risk_score),
        riskLevel:     level,
        sentimentGap:  f(row.sentiment_gap),
        coverageRisk:  f(row.coverage_risk),
      },
    });
  }

  // ── 3. Platform summaries ─────────────────────────────────────────────────

  for (const row of summaryRows) {
    const placeId = row.place_id;
    const platform = row.platform as Platform;

    await prisma.platformSummary.upsert({
      where: { placeId_platform: { placeId, platform } },
      create: {
        placeId,
        platform,
        recordCount:            parseInt(row.record_count ?? "0", 10),
        usefulRecordCount:      parseInt(row.useful_record_count ?? "0", 10),
        avgSentimentScore:      f(row.avg_sentiment_score),
        negativeSentimentRatio: f(row.negative_sentiment_ratio),
        avgQualityScore:        f(row.avg_quality_score),
        avgServiceScore:        f(row.avg_service_score),
        avgPriceScore:          f(row.avg_price_score),
        avgSceneryScore:        f(row.avg_scenery_score),
        avgCrowdedScore:        f(row.avg_crowded_score),
        avgFoodDrinkScore:      f(row.avg_food_drink_score),
        avgCleanlinessScore:    f(row.avg_cleanliness_score),
        avgLocationScore:       f(row.avg_location_score),
        googleMapsRatingAvg:    row.google_maps_rating_avg_from_reviews ? f(row.google_maps_rating_avg_from_reviews) : null,
        googleMapsRatingMaster: row.google_maps_rating_master ? f(row.google_maps_rating_master) : null,
      },
      update: {
        avgSentimentScore:  f(row.avg_sentiment_score),
        avgQualityScore:    f(row.avg_quality_score),
        recordCount:        parseInt(row.record_count ?? "0", 10),
      },
    });
  }

  // ── 4. Reviews (sample — first 100 to keep seed fast) ────────────────────

  const sampleReviews = reviewRows.slice(0, 100);
  for (const row of sampleReviews) {
    const trustLevel = (row.trust_level?.toLowerCase() ?? "low") as TrustLevel;

    await prisma.review.upsert({
      where: { id: row.normalized_id },
      create: {
        id:               row.normalized_id,
        placeId:          row.place_id,
        platform:         row.platform as Platform,
        contentText:      row.content_text || null,
        translatedTextVi: row.translated_text_vi || null,
        language:         row.language || null,
        rating:           row.rating ? f(row.rating) : null,
        finalTrustScore:  f(row.final_trust_score),
        trustLevel,
        qualityScore:     f(row.quality_score),
        sentimentScore:   f(row.sentiment_score),
        serviceScore:     f(row.service_score),
        priceScore:       f(row.price_score),
        sceneryScore:     f(row.scenery_score),
        hasRiskFlag:      row.has_risk_flag === "True",
        riskFlags:        row.risk_flags ? row.risk_flags.split("|").filter(Boolean) : [],
        authorKey:        row.author_key || row.author_id_or_name || "unknown",
        engagementCount:  parseInt(row.engagement_count ?? "0", 10),
        contentCreatedAt: row.content_created_at ? new Date(row.content_created_at) : null,
        scrapedAt:        row.scraped_at ? new Date(row.scraped_at) : new Date(),
      },
      update: {},  // reviews are immutable — don't overwrite on re-seed
    });
  }

  console.log(`  ✓ ${riskRows.length} real place(s) from CSV`);

  // ── 5. Mock places (for dev/testing UI diversity) ─────────────────────────
  // TODO: replace with real pipeline output when more places are crawled

  for (const mp of MOCK_PLACES) {
    await prisma.place.upsert({
      where: { id: mp.id },
      create: {
        id: mp.id,
        name: mp.name,
        category: mp.category,
        address: mp.address,
        lat: mp.lat,
        lng: mp.lng,
        googleMapsRating: mp.googleMapsRating,
        weightedRating: mp.weightedRating,
      },
      update: {},
    });

    await prisma.riskScore.upsert({
      where: { placeId: mp.id },
      create: {
        placeId: mp.id,
        riskScore: mp.riskScore,
        riskLevel: mp.riskLevel,
      },
      update: {},
    });
  }

  console.log(`  ✓ ${MOCK_PLACES.length} mock places inserted`);
  console.log("🌱 Seed complete.");
}

main()
  .catch((e) => { console.error("❌ Seed failed:", e); process.exit(1); })
  .finally(() => prisma.$disconnect());
