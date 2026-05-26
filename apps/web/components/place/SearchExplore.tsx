"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import PlaceCard from "./PlaceCard";
import { searchPlaces, type PlaceListItem, type RiskLevel, type PageMeta } from "@/lib/api";

const CATEGORIES = [
  "Quán cà phê",
  "Nhà hàng",
  "Địa điểm du lịch",
  "Lưu trú",
  "Mua sắm",
  "Giải trí",
];

const RISK_CHIPS: { key: RiskLevel | "all"; label: string; style: React.CSSProperties }[] = [
  { key: "all",    label: "Tất cả",    style: { background: "var(--g)", color: "#fff" } },
  { key: "low",    label: "Tin cậy",   style: { background: "rgba(140,167,10,.1)", color: "var(--l)", borderColor: "var(--l)" } },
  { key: "medium", label: "Lưu ý",    style: { background: "rgba(238,182,39,.12)", color: "#a07800", borderColor: "var(--y)" } },
  { key: "high",   label: "Rủi ro",   style: { background: "rgba(223,111,59,.1)", color: "var(--o)", borderColor: "var(--o)" } },
];

export default function SearchExplore() {
  const router         = useRouter();
  const searchParams   = useSearchParams();

  const [query,    setQuery]    = useState(searchParams.get("q")        ?? "");
  const [category, setCategory] = useState(searchParams.get("category") ?? "");
  const [riskLevel,setRiskLevel]= useState<RiskLevel | "all">((searchParams.get("risk") as RiskLevel) ?? "all");

  const [places,   setPlaces]   = useState<PlaceListItem[]>([]);
  const [meta,     setMeta]     = useState<PageMeta | null>(null);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState<string | null>(null);

  const load = useCallback(async (q: string, cat: string, risk: RiskLevel | "all") => {
    setLoading(true);
    setError(null);
    const res = await searchPlaces({
      q:          q || undefined,
      category:   cat || undefined,
      risk_level: risk === "all" ? undefined : risk,
      page_size:  24,
    });
    if (res.ok) {
      setPlaces((res as typeof res & { meta: PageMeta }).data);
      setMeta((res as typeof res & { meta: PageMeta }).meta ?? null);
    } else {
      setError(res.error);
      setPlaces([]);
    }
    setLoading(false);
  }, []);

  // Initial load
  useEffect(() => { load(query, category, riskLevel); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync URL without triggering navigation
  useEffect(() => {
    const params = new URLSearchParams();
    if (query)              params.set("q",        query);
    if (category)           params.set("category", category);
    if (riskLevel !== "all") params.set("risk",    riskLevel);
    router.replace(`/?${params.toString()}`, { scroll: false });
  }, [query, category, riskLevel, router]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    load(query, category, riskLevel);
  }

  function selectRisk(r: RiskLevel | "all") {
    setRiskLevel(r);
    load(query, category, r);
  }

  function selectCategory(e: React.ChangeEvent<HTMLSelectElement>) {
    const cat = e.target.value;
    setCategory(cat);
    load(query, cat, riskLevel);
  }

  return (
    <section style={{ maxWidth: 1160, margin: "0 auto", padding: "36px 28px" }}>
      {/* Header */}
      <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--g)", marginBottom: 5, fontFamily: "Unbounded, sans-serif" }}>
        Khám phá địa điểm
      </h2>
      <p style={{ fontSize: 13, color: "var(--tm)", marginBottom: 20 }}>
        {meta ? `${meta.total} địa điểm tại Đà Lạt` : "Đang tải…"}
      </p>

      {/* Search bar */}
      <form onSubmit={handleSearch} style={{ display: "flex", gap: 10, marginBottom: 18, flexWrap: "wrap" }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Tìm theo tên địa điểm…"
          style={{
            flex: 1, minWidth: 220,
            background: "#fff",
            border: "2px solid rgba(11,89,47,.1)",
            borderRadius: 12,
            padding: "11px 16px",
            fontSize: 13.5,
            color: "var(--tx)",
            outline: "none",
            fontFamily: "inherit",
          }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "var(--g)"; }}
          onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(11,89,47,.1)"; }}
        />
        <select
          value={category}
          onChange={selectCategory}
          style={{
            background: "#fff",
            border: "2px solid rgba(11,89,47,.1)",
            borderRadius: 12,
            padding: "11px 14px",
            fontFamily: "inherit",
            fontSize: 13,
            color: "var(--tx)",
            outline: "none",
          }}
        >
          <option value="">Tất cả loại</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <button
          type="submit"
          style={{
            background: "var(--g)", color: "#fff",
            border: "none", padding: "11px 22px",
            borderRadius: 12, fontSize: 13, fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Tìm kiếm
        </button>
      </form>

      {/* Risk level chips */}
      <div style={{ display: "flex", gap: 7, marginBottom: 22, flexWrap: "wrap" }}>
        {RISK_CHIPS.map(({ key, label, style }) => (
          <button
            key={key}
            onClick={() => selectRisk(key)}
            style={{
              padding: "6px 13px",
              borderRadius: 18,
              fontSize: 11.5,
              fontWeight: 600,
              border: "2px solid transparent",
              cursor: "pointer",
              transition: ".2s",
              ...(riskLevel === key ? style : { background: "transparent", color: "var(--tm)", borderColor: "var(--cd)" }),
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* States */}
      {loading && (
        <div style={{ textAlign: "center", padding: "60px 0", color: "var(--tm)", fontSize: 14 }}>
          Đang tải địa điểm…
        </div>
      )}

      {!loading && error && (
        <div style={{
          textAlign: "center", padding: "60px 0",
          background: "rgba(223,111,59,.06)",
          border: "1.5px solid rgba(223,111,59,.2)",
          borderRadius: 16, color: "var(--o)",
        }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>⚠️</div>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>Không thể kết nối API</div>
          <div style={{ fontSize: 12, opacity: .7 }}>{error}</div>
        </div>
      )}

      {!loading && !error && places.length === 0 && (
        <div style={{ textAlign: "center", padding: "60px 0", color: "var(--tm)", fontSize: 14 }}>
          Không tìm thấy địa điểm phù hợp.
        </div>
      )}

      {/* Place grid */}
      {!loading && places.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill,minmax(270px,1fr))",
            gap: 18,
          }}
        >
          {places.map((p) => <PlaceCard key={p.id} place={p} />)}
        </div>
      )}
    </section>
  );
}
