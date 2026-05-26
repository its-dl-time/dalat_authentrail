import Link from "next/link";
import { notFound } from "next/navigation";
import { getPlace } from "@/lib/api";
import ScoreBanner from "@/components/place/ScoreBanner";
import RiskBreakdown from "@/components/place/RiskBreakdown";
import PlatformRows from "@/components/place/PlatformRows";
import RiskChip from "@/components/ui/RiskChip";
import PlaceCommunity from "@/components/community/PlaceCommunity";
import type { CrowdLevel } from "@/lib/api";
import type { Metadata } from "next";

// ─── Category thumbnail gradients ──────────────────────────────────────────────
const GRADIENTS: Record<string, string> = {
  "Quán cà phê":      "linear-gradient(135deg,#936440,#DF6F3B)",
  "Nhà hàng":         "linear-gradient(135deg,#0B592F,#8CA70A)",
  "Địa điểm du lịch": "linear-gradient(135deg,#083d20,#0B592F)",
  "Lưu trú":          "linear-gradient(135deg,#4a6fa5,#2d4a7a)",
  "Mua sắm":          "linear-gradient(135deg,#EEB627,#DF6F3B)",
  "Giải trí":         "linear-gradient(135deg,#8CA70A,#0B592F)",
};

// ─── LiveStatus card (server component — no interactivity needed) ─────────────

const CROWD_LABEL: Record<CrowdLevel, { text: string; color: string; emoji: string }> = {
  very_busy: { text: "Rất đông",     color: "#EA4335", emoji: "🔴" },
  busy:      { text: "Đông",         color: "#DF6F3B", emoji: "🟠" },
  moderate:  { text: "Bình thường",  color: "#EEB627", emoji: "🟡" },
  empty:     { text: "Vắng",         color: "#8CA70A", emoji: "🟢" },
  unknown:   { text: "Chưa rõ",      color: "#6b6b6b", emoji: "⚪" },
};

interface LiveStatusProps {
  crowded: CrowdLevel; confidence: number; answerCount: number;
  priceNote?: string | null; viewNote?: string | null; recommendedToGo?: boolean | null;
  lastVerifiedAt: string; expiresAt: string;
}
function LiveStatusCard({ status }: { status: LiveStatusProps }) {
  const cfg    = CROWD_LABEL[status.crowded];
  const confPct = Math.round(status.confidence * 100);

  return (
    <div
      style={{
        background: "#fff", borderRadius: 16, padding: 18,
        border: "1px solid rgba(11,89,47,.06)", marginBottom: 14,
      }}
    >
      <div style={{ fontFamily: "Unbounded, sans-serif", fontSize: 12.5, fontWeight: 700, color: "var(--g)", marginBottom: 12 }}>
        📡 Tình trạng hiện tại
      </div>

      {/* Crowd level */}
      <div
        style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          background: `${cfg.color}0f`, borderRadius: 10, padding: "10px 12px", marginBottom: 10,
        }}
      >
        <span style={{ fontSize: 13, fontWeight: 600, color: cfg.color }}>
          {cfg.emoji} {cfg.text}
        </span>
        <span style={{ fontSize: 11, color: "var(--tm)" }}>
          {status.answerCount} phản hồi · {confPct}%
        </span>
      </div>

      {status.priceNote && (
        <div style={{ fontSize: 12, color: "var(--tm)", marginBottom: 6, lineHeight: 1.5 }}>
          💰 {status.priceNote}
        </div>
      )}
      {status.viewNote && (
        <div style={{ fontSize: 12, color: "var(--tm)", marginBottom: 6, lineHeight: 1.5 }}>
          📷 {status.viewNote}
        </div>
      )}
      {status.recommendedToGo !== null && status.recommendedToGo !== undefined && (
        <div style={{ fontSize: 12, fontWeight: 600, color: status.recommendedToGo ? "var(--g)" : "var(--o)" }}>
          {status.recommendedToGo ? "✅ Cộng đồng khuyên đến" : "⚠️ Cộng đồng không khuyên đến"}
        </div>
      )}

      <div style={{ fontSize: 10.5, color: "var(--tm)", marginTop: 8, borderTop: "1px solid rgba(0,0,0,.05)", paddingTop: 8 }}>
        Cập nhật từ cộng đồng · Hết hạn {new Date(status.expiresAt).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}
      </div>
    </div>
  );
}

// ─── Metadata ─────────────────────────────────────────────────────────────────
export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const res = await getPlace(id);
  if (!res.ok) return { title: "Địa điểm | DaLat Authentrail" };
  return {
    title:       `${res.data.name} | DaLat Authentrail`,
    description: `Xem đánh giá tin cậy cho ${res.data.name} tại Đà Lạt.`,
  };
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default async function PlaceDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const res = await getPlace(id);

  if (!res.ok) notFound();

  const place = res.data;
  const gradient = GRADIENTS[place.category] ?? "linear-gradient(135deg,#936440,#0B592F)";

  return (
    <div style={{ paddingTop: 60, minHeight: "100vh" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "36px 28px" }}>
        {/* Back button */}
        <Link
          href="/"
          style={{
            display: "inline-flex", alignItems: "center", gap: 7,
            fontSize: 12.5, fontWeight: 600, color: "var(--g)",
            padding: "7px 14px", background: "rgba(11,89,47,.07)",
            borderRadius: 18, textDecoration: "none", marginBottom: 24,
            transition: ".2s",
          }}
        >
          ← Quay lại
        </Link>

        {/* Two-column layout */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 340px",
            gap: 20,
            alignItems: "start",
          }}
        >
          {/* ── Main column ── */}
          <div>
            {/* Image / gradient hero */}
            <div
              style={{
                borderRadius: 18, overflow: "hidden",
                height: 260, position: "relative",
                background: gradient, marginBottom: 16,
                display: "flex", alignItems: "flex-end",
              }}
            >
              <div
                style={{
                  position: "absolute", inset: 0,
                  background: "linear-gradient(to top, rgba(0,0,0,.55), transparent)",
                }}
              />
              {/* Category chip */}
              <div
                style={{
                  position: "absolute", top: 14, left: 14,
                  background: "rgba(255,255,255,.18)",
                  backdropFilter: "blur(6px)", color: "#fff",
                  padding: "4px 10px", borderRadius: 9,
                  fontSize: 10, fontWeight: 600, letterSpacing: 1,
                  textTransform: "uppercase",
                }}
              >
                {place.category}
              </div>
              {/* Name overlay */}
              <div style={{ position: "relative", padding: "0 0 16px 16px" }}>
                <div style={{ fontFamily: "Unbounded, sans-serif", fontSize: 20, fontWeight: 900, color: "#fff", marginBottom: 3 }}>
                  {place.name}
                </div>
                {place.address && (
                  <div style={{ fontSize: 12.5, color: "rgba(255,255,255,.8)" }}>
                    📍 {place.address}
                  </div>
                )}
              </div>
            </div>

            {/* Score banner */}
            <ScoreBanner place={place} />

            {/* Risk breakdown */}
            {place.riskScore && <RiskBreakdown risk={place.riskScore} />}

            {/* Platform comparison */}
            {place.platformSummaries.length > 0 && (
              <PlatformRows summaries={place.platformSummaries} />
            )}

            {/* Google Maps link */}
            {place.googleMapsUrl && (
              <div style={{ marginBottom: 14 }}>
                <a
                  href={place.googleMapsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "14px 16px", borderRadius: 11, background: "var(--c)",
                    textDecoration: "none", border: "1.5px solid transparent",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#EA4335" }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--tx)" }}>Xem trên Google Maps</span>
                  </div>
                  <span style={{ fontSize: 14, color: "var(--g)", fontWeight: 700 }}>→</span>
                </a>
              </div>
            )}

            {/* Community Q&A — Task 2.4 */}
            <div style={{ background: "#fff", borderRadius: 16, padding: 18, border: "1px solid rgba(11,89,47,.08)" }}>
              <PlaceCommunity placeId={place.id} />
            </div>
          </div>

          {/* ── Sidebar ── */}
          <div>
            {/* Meta card */}
            <div
              style={{
                background: "var(--g)", color: "#fff",
                borderRadius: 16, padding: 18, marginBottom: 14,
              }}
            >
              <div style={{ fontSize: 9.5, letterSpacing: 1.5, textTransform: "uppercase", opacity: .6, marginBottom: 12 }}>
                Thông tin địa điểm
              </div>

              {[
                { k: "Loại hình",     v: place.category },
                { k: "Địa chỉ",      v: place.address ?? "Đà Lạt" },
                { k: "Toạ độ",       v: `${place.lat.toFixed(4)}, ${place.lng.toFixed(4)}` },
                { k: "Google Rating", v: place.googleMapsRating ? `${place.googleMapsRating} / 5` : "—" },
                { k: "Weighted",     v: place.weightedRating ? `${place.weightedRating.toFixed(2)} / 5` : "—" },
              ].map(({ k, v }) => (
                <div
                  key={k}
                  style={{
                    display: "flex", justifyContent: "space-between", alignItems: "center",
                    padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,.1)",
                  }}
                >
                  <span style={{ fontSize: 11.5, opacity: .7 }}>{k}</span>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{v}</span>
                </div>
              ))}

              {/* Risk summary */}
              {place.riskScore && (
                <div style={{ marginTop: 16, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: 11.5, opacity: .7 }}>Mức rủi ro</span>
                  <RiskChip level={place.riskScore.riskLevel} />
                </div>
              )}
            </div>

            {/* Live status */}
            {place.liveStatus && <LiveStatusCard status={place.liveStatus} />}

            {/* Similar places placeholder */}
            <div
              style={{
                background: "#fff", borderRadius: 16, padding: 18,
                border: "1px solid rgba(11,89,47,.06)",
              }}
            >
              <div style={{ fontFamily: "Unbounded, sans-serif", fontSize: 12.5, fontWeight: 700, color: "var(--g)", marginBottom: 10 }}>
                Gợi ý tương tự
              </div>
              <p style={{ fontSize: 12, color: "var(--tm)" }}>
                Địa điểm tương tự sẽ được gợi ý sau khi có thêm dữ liệu pipeline.
                {/* TODO: fetch similar places by category + risk level */}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
