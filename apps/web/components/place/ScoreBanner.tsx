import type { PlaceFull } from "@/lib/api";

const PLATFORM_LABELS: Record<string, string> = {
  google_maps: "Google",
  facebook:    "Facebook",
  tiktok:      "TikTok",
};

function scoreLabel(score: number) {
  if (score >= 4.2) return "Rất đáng tin";
  if (score >= 3.5) return "Tốt";
  if (score >= 2.5) return "Cần cân nhắc";
  return "Nhiều rủi ro";
}

export default function ScoreBanner({ place }: { place: PlaceFull }) {
  const score = place.weightedRating ?? place.googleMapsRating ?? 0;

  return (
    <div
      style={{
        background: "var(--g)", color: "#fff",
        borderRadius: 16, padding: "18px 20px",
        marginBottom: 16,
        display: "flex", alignItems: "center", gap: 20,
      }}
    >
      {/* Rating ring */}
      <div
        style={{
          width: 64, height: 64, borderRadius: "50%",
          border: "3px solid var(--l)",
          display: "grid", placeItems: "center",
          fontFamily: "Unbounded, sans-serif",
          fontSize: 22, fontWeight: 900,
          flexShrink: 0,
        }}
      >
        {score.toFixed(1)}
      </div>

      {/* Info */}
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: "var(--l)", marginBottom: 4 }}>
          {scoreLabel(score)}
        </div>
        <div style={{ fontSize: 11.5, opacity: .7, lineHeight: 1.5 }}>
          Điểm tổng hợp có trọng số từ đánh giá đa nền tảng
        </div>
      </div>

      {/* Per-platform scores */}
      {place.platformSummaries.length > 0 && (
        <div style={{ display: "flex", gap: 8, marginLeft: "auto" }}>
          {place.platformSummaries.map((ps) => (
            <div
              key={ps.platform}
              style={{
                background: "rgba(255,255,255,.12)",
                borderRadius: 9, padding: "8px 12px",
                textAlign: "center", minWidth: 68,
              }}
            >
              <div style={{ fontSize: 9, opacity: .6, letterSpacing: .8, textTransform: "uppercase", marginBottom: 3 }}>
                {PLATFORM_LABELS[ps.platform] ?? ps.platform}
              </div>
              <div style={{ fontFamily: "Unbounded, sans-serif", fontSize: 16, fontWeight: 700, color: "var(--l)" }}>
                {ps.avgSentimentScore > 0
                  ? (ps.avgSentimentScore * 5).toFixed(1)
                  : (ps.googleMapsRatingAvg ?? "—")}
              </div>
              <div style={{ fontSize: 8.5, opacity: .5, marginTop: 1 }}>
                {ps.recordCount} đánh giá
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
