import type { PlatformSummary } from "@/lib/api";

const PLATFORM_CONFIG: Record<string, { name: string; color: string; dot: string }> = {
  google_maps: { name: "Google Maps", color: "#EA4335", dot: "#EA4335" },
  facebook:    { name: "Facebook",    color: "#4267B2", dot: "#4267B2" },
  tiktok:      { name: "TikTok",      color: "#000000", dot: "#333"   },
};

const DIMENSIONS = [
  { key: "avgServiceScore",     label: "Dịch vụ"    },
  { key: "avgPriceScore",       label: "Giá cả"     },
  { key: "avgSceneryScore",     label: "Cảnh quan"  },
  { key: "avgFoodDrinkScore",   label: "Ẩm thực"   },
  { key: "avgCleanlinessScore", label: "Vệ sinh"    },
  { key: "avgLocationScore",    label: "Vị trí"     },
] as const;

export default function PlatformRows({ summaries }: { summaries: PlatformSummary[] }) {
  if (summaries.length === 0) return null;

  return (
    <div
      style={{
        background: "#fff", borderRadius: 16,
        padding: 20, border: "1px solid rgba(11,89,47,.06)",
        marginBottom: 14,
      }}
    >
      <div
        style={{
          fontFamily: "Unbounded, sans-serif",
          fontSize: 12.5, fontWeight: 700, color: "var(--g)",
          marginBottom: 14,
        }}
      >
        So sánh nền tảng
      </div>

      {summaries.map((ps) => {
        const cfg = PLATFORM_CONFIG[ps.platform] ?? { name: ps.platform, color: "var(--tm)", dot: "var(--tm)" };
        return (
          <div
            key={ps.platform}
            style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "14px 16px",
              borderRadius: 11, background: "var(--c)",
              marginBottom: 9,
              border: "1.5px solid transparent",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 10, height: 10, borderRadius: "50%", background: cfg.dot, flexShrink: 0 }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "var(--tx)", marginBottom: 2 }}>
                  {cfg.name}
                </div>
                <div style={{ fontSize: 11, color: "var(--tm)" }}>
                  {ps.usefulRecordCount} / {ps.recordCount} đánh giá hữu ích
                  {ps.negativeSentimentRatio > 0 && (
                    <span style={{ marginLeft: 8, color: "var(--o)" }}>
                      {(ps.negativeSentimentRatio * 100).toFixed(0)}% tiêu cực
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, color: "var(--g)", fontFamily: "Unbounded, sans-serif" }}>
              {ps.googleMapsRatingMaster
                ? ps.googleMapsRatingMaster.toFixed(1)
                : (ps.avgSentimentScore * 5).toFixed(1)}
            </div>
          </div>
        );
      })}

      {/* Dimension grid (first platform's scores as representative) */}
      {summaries[0] && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill,minmax(120px,1fr))",
            gap: 8,
            marginTop: 8,
          }}
        >
          {DIMENSIONS.map(({ key, label }) => {
            const val = summaries[0][key] as number;
            if (!val) return null;
            return (
              <div key={key} style={{ background: "var(--c)", borderRadius: 10, padding: 10, textAlign: "center" }}>
                <div style={{ fontSize: 10, color: "var(--tm)", marginBottom: 4 }}>{label}</div>
                <div style={{ fontFamily: "Unbounded, sans-serif", fontSize: 16, fontWeight: 700, color: "var(--g)" }}>
                  {(val * 5).toFixed(1)}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
