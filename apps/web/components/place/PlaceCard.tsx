import Link from "next/link";
import Image from "next/image";
import RiskChip from "@/components/ui/RiskChip";
import LiveDot from "@/components/ui/LiveDot";
import type { PlaceListItem } from "@/lib/api";

// Category → gradient for when there's no real image
const GRADIENTS: Record<string, string> = {
  "Quán cà phê":       "linear-gradient(135deg,#936440,#DF6F3B)",
  "Nhà hàng":          "linear-gradient(135deg,#0B592F,#8CA70A)",
  "Địa điểm du lịch":  "linear-gradient(135deg,#083d20,#0B592F)",
  "Lưu trú":           "linear-gradient(135deg,#4a6fa5,#2d4a7a)",
  "Mua sắm":           "linear-gradient(135deg,#EEB627,#DF6F3B)",
  "Giải trí":          "linear-gradient(135deg,#8CA70A,#0B592F)",
};

function thumbGradient(category: string) {
  return GRADIENTS[category] ?? "linear-gradient(135deg,#936440,#0B592F)";
}

export default function PlaceCard({ place }: { place: PlaceListItem }) {
  const score = place.weightedRating ?? place.googleMapsRating ?? 0;
  const pct   = Math.min(100, (score / 5) * 100);
  const hasLive = !!place.liveStatus && new Date(place.liveStatus.expiresAt) > new Date();

  return (
    <Link
      href={`/places/${place.id}`}
      className="block no-underline"
      style={{
        background: "#fff",
        borderRadius: 16,
        overflow: "hidden",
        cursor: "pointer",
        border: "1px solid rgba(11,89,47,.05)",
        transition: ".3s",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLAnchorElement).style.transform = "translateY(-4px)";
        (e.currentTarget as HTMLAnchorElement).style.boxShadow = "0 14px 36px rgba(11,89,47,.13)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLAnchorElement).style.transform = "";
        (e.currentTarget as HTMLAnchorElement).style.boxShadow = "";
      }}
    >
      {/* Thumbnail */}
      <div
        style={{
          height: 148,
          position: "relative",
          display: "flex",
          alignItems: "flex-end",
          padding: 10,
          background: place.coverImageUrl ? undefined : thumbGradient(place.category),
        }}
      >
        {place.coverImageUrl && (
          <Image
            src={place.coverImageUrl}
            alt={place.name}
            fill
            className="object-cover"
          />
        )}

        {/* Risk badge — top right */}
        {place.riskScore && (
          <RiskChip
            level={place.riskScore.riskLevel}
            className="absolute top-[10px] right-[10px]"
          />
        )}

        {/* Category chip — bottom left */}
        <span
          style={{
            background: "rgba(255,255,255,.18)",
            backdropFilter: "blur(5px)",
            color: "#fff",
            padding: "3px 9px",
            borderRadius: 8,
            fontSize: 9.5,
            fontWeight: 600,
            letterSpacing: 1,
            textTransform: "uppercase",
            position: "relative",
          }}
        >
          {place.category}
        </span>
      </div>

      {/* Body */}
      <div style={{ padding: 14 }}>
        <div style={{ fontFamily: "Unbounded, sans-serif", fontSize: 13, fontWeight: 700, color: "var(--g)", marginBottom: 3 }}>
          {place.name}
        </div>
        <div style={{ fontSize: 11.5, color: "var(--tm)", marginBottom: 10 }}>
          {place.address ?? "Đà Lạt"}
        </div>

        {/* Score row */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
          <span style={{ fontFamily: "Unbounded, sans-serif", fontSize: 22, fontWeight: 900, color: "var(--g)" }}>
            {score.toFixed(1)}
          </span>
          <div style={{ flex: 1, height: 5, background: "var(--cd)", borderRadius: 3, overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${pct}%`, background: "linear-gradient(90deg,var(--l),var(--g))", borderRadius: 3 }} />
          </div>
        </div>

        {/* Footer */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 11, color: "var(--tm)" }}>
            {place.googleMapsRating ? `★ ${place.googleMapsRating} Google Maps` : "Chưa có đánh giá"}
          </span>
          {hasLive && (
            <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: "var(--l)", fontWeight: 600 }}>
              <LiveDot />
              Live
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
