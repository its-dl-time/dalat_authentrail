import type { RiskScore } from "@/lib/api";

interface Dimension {
  key:   keyof RiskScore;
  label: string;
}

const DIMENSIONS: Dimension[] = [
  { key: "sentimentGap",            label: "Chênh lệch cảm xúc"      },
  { key: "negativeSocialVsMapsGap", label: "Tỷ lệ tiêu cực MXH vs Maps" },
  { key: "topicGap",                label: "Chủ đề bị bỏ qua"         },
  { key: "engagementGap",           label: "Chênh lệch tương tác"     },
  { key: "coverageRisk",            label: "Độ phủ dữ liệu"            },
  { key: "dataQualityRisk",         label: "Chất lượng dữ liệu"        },
];

export default function RiskBreakdown({ risk }: { risk: RiskScore }) {
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
          marginBottom: 12, display: "flex", alignItems: "center", gap: 7,
        }}
      >
        ⚠️ Phân tích rủi ro
      </div>

      {/* Overall risk score bar */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: 12 }}>
          <span style={{ color: "var(--tm)" }}>Điểm rủi ro tổng</span>
          <span style={{ fontWeight: 700, color: "var(--o)" }}>
            {Math.round(risk.riskScore * 100)}%
          </span>
        </div>
        <div style={{ height: 8, background: "var(--cd)", borderRadius: 4, overflow: "hidden" }}>
          <div
            style={{
              height: "100%",
              width: `${risk.riskScore * 100}%`,
              background: risk.riskLevel === "high"
                ? "var(--o)"
                : risk.riskLevel === "medium"
                ? "var(--y)"
                : "var(--l)",
              borderRadius: 4,
            }}
          />
        </div>
      </div>

      {/* Sub-dimension bars */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {DIMENSIONS.map(({ key, label }) => {
          const val = risk[key] as number;
          return (
            <div key={key}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 11.5 }}>
                <span style={{ color: "var(--tm)" }}>{label}</span>
                <span style={{ fontWeight: 600, color: "var(--tx)" }}>{(val * 100).toFixed(0)}%</span>
              </div>
              <div style={{ height: 4, background: "var(--cd)", borderRadius: 2, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${val * 100}%`, background: "var(--o)", borderRadius: 2 }} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Top complaints */}
      {risk.topComplaints.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "var(--o)", marginBottom: 8, textTransform: "uppercase", letterSpacing: .5 }}>
            Phàn nàn nổi bật
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {risk.topComplaints.map((c, i) => (
              <div
                key={i}
                style={{
                  display: "flex", alignItems: "flex-start", gap: 10,
                  padding: "11px 13px",
                  background: "rgba(223,111,59,.05)",
                  borderRadius: 10, border: "1px solid rgba(223,111,59,.12)",
                }}
              >
                <span style={{ fontSize: 13, flexShrink: 0, marginTop: 1 }}>⚡</span>
                <span style={{ fontSize: 12.5, color: "var(--tx)", lineHeight: 1.55 }}>{c}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sentiment comparison */}
      <div
        style={{
          marginTop: 16, display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 10,
        }}
      >
        {[
          { label: "Google Maps sentiment", val: risk.googleMapsAvgSentiment },
          { label: "Mạng xã hội sentiment", val: risk.socialAvgSentiment },
        ].map(({ label, val }) => (
          <div key={label} style={{ background: "var(--c)", borderRadius: 10, padding: 12 }}>
            <div style={{ fontSize: 10, color: "var(--tm)", marginBottom: 4 }}>{label}</div>
            <div style={{ fontFamily: "Unbounded, sans-serif", fontSize: 18, fontWeight: 700, color: val >= 0.6 ? "var(--l)" : "var(--o)" }}>
              {(val * 100).toFixed(0)}%
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
