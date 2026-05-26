import { Suspense } from "react";
import SearchExplore from "@/components/place/SearchExplore";

export default function HomePage() {
  return (
    <main style={{ paddingTop: 60 }}>
      {/* Hero */}
      <div style={{ background: "var(--c)", borderBottom: "1px solid rgba(11,89,47,.08)" }}>
        <div style={{ maxWidth: 1160, margin: "0 auto", padding: "56px 28px 40px" }}>
          <div
            style={{
              display: "inline-flex", alignItems: "center", gap: 6,
              background: "rgba(11,89,47,.08)", border: "1px solid rgba(11,89,47,.2)",
              borderRadius: 18, padding: "5px 13px",
              fontSize: 10.5, fontWeight: 600, color: "var(--g)",
              letterSpacing: 1, textTransform: "uppercase", marginBottom: 20,
            }}
          >
            <span className="live-dot" />
            Đánh giá đa nguồn · Thời gian thực
          </div>

          <h1
            style={{
              fontFamily: "Unbounded, sans-serif",
              fontSize: "clamp(28px,4vw,52px)",
              fontWeight: 900, lineHeight: 1.05,
              color: "var(--g)", marginBottom: 14,
            }}
          >
            Địa điểm nào thực sự<br />
            <em style={{ fontStyle: "italic", color: "var(--o)" }}>đáng tin</em> ở Đà Lạt?
          </h1>

          <p style={{ fontSize: 14, color: "var(--tm)", lineHeight: 1.75, maxWidth: 480 }}>
            Chúng tôi tổng hợp đánh giá từ Google Maps, Facebook và TikTok —
            phân tích mức độ tin cậy thực sự của từng địa điểm.
          </p>

          <div style={{ display: "flex", gap: 28, marginTop: 32, paddingTop: 24, borderTop: "1px solid rgba(11,89,47,.1)" }}>
            {[
              { n: "285+", l: "Đánh giá phân tích" },
              { n: "3",    l: "Nền tảng" },
              { n: "100%", l: "Minh bạch" },
            ].map(({ n, l }) => (
              <div key={l}>
                <div style={{ fontFamily: "Unbounded, sans-serif", fontSize: 20, fontWeight: 700, color: "var(--g)" }}>{n}</div>
                <div style={{ fontSize: 11, color: "var(--tm)", marginTop: 2 }}>{l}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Search + Grid */}
      <Suspense fallback={
        <div style={{ textAlign: "center", padding: "60px 0", color: "var(--tm)" }}>Đang tải…</div>
      }>
        <SearchExplore />
      </Suspense>
    </main>
  );
}
