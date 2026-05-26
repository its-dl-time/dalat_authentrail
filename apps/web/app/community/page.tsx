"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import type { Question, AuthHeaders } from "@/lib/api";
import { getQuestions } from "@/lib/api";
import { useSocket } from "@/hooks/useSocket";
import QuestionCard from "@/components/community/QuestionCard";

export default function CommunityPage() {
  const { data: session } = useSession();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [page,      setPage]      = useState(1);
  const [hasMore,   setHasMore]   = useState(false);

  const auth: AuthHeaders | undefined = session?.user
    ? {
        "X-User-Id":    (session.user as { id?: string }).id ?? "",
        "X-User-Email": session.user.email ?? "",
        "X-User-Name":  session.user.name  ?? "Người dùng",
      }
    : undefined;

  const load = useCallback(async (p: number, append = false) => {
    setLoading(true);
    const res = await getQuestions({ page: p, page_size: 15 });
    if (res.ok) {
      setQuestions((prev) => (append ? [...prev, ...res.data] : res.data));
      const meta = (res as unknown as { meta?: { totalPages: number } }).meta;
      setHasMore(!!meta && p < meta.totalPages);
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(1); }, [load]);

  // Listen for new questions globally (no placeId → no room, so no socket needed here)
  // Questions are added via manual refresh or after posting on a place page
  useSocket(undefined, {});

  return (
    <div style={{ paddingTop: 60, minHeight: "100vh" }}>
      <div style={{ maxWidth: 720, margin: "0 auto", padding: "36px 20px" }}>

        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <div
            style={{
              display: "inline-flex", alignItems: "center", gap: 6,
              background: "rgba(11,89,47,.08)", border: "1px solid rgba(11,89,47,.2)",
              borderRadius: 18, padding: "5px 13px",
              fontSize: 10.5, fontWeight: 600, color: "var(--g)",
              letterSpacing: 1, textTransform: "uppercase", marginBottom: 14,
            }}
          >
            <span
              style={{
                width: 5, height: 5, borderRadius: "50%",
                background: "var(--l)", display: "inline-block",
                animation: "pulse 2s infinite",
              }}
            />
            Cộng đồng
          </div>
          <h1
            style={{
              fontFamily: "Unbounded, sans-serif",
              fontSize: "clamp(22px, 3.5vw, 34px)",
              fontWeight: 900, color: "var(--g)",
              lineHeight: 1.1, marginBottom: 10,
            }}
          >
            Hỏi đáp thực tế
          </h1>
          <p style={{ fontSize: 13.5, color: "var(--tm)", lineHeight: 1.7, maxWidth: 480 }}>
            Câu hỏi từ những người đã hoặc đang có mặt tại các địa điểm Đà Lạt.
            Trả lời thực tế, bình chọn để lên top.
          </p>
        </div>

        {/* CTA if not logged in */}
        {!session && (
          <div
            style={{
              background: "var(--g)", borderRadius: 14, padding: "16px 20px",
              marginBottom: 24, display: "flex", alignItems: "center",
              justifyContent: "space-between", gap: 12,
            }}
          >
            <p style={{ fontSize: 13, color: "rgba(255,255,255,.85)", lineHeight: 1.5 }}>
              Đăng nhập để đặt câu hỏi và trả lời về các địa điểm bạn đã ghé.
            </p>
            <Link
              href="/auth/signin"
              style={{
                flexShrink: 0, background: "#fff", color: "var(--g)",
                padding: "8px 16px", borderRadius: 10,
                fontSize: 12.5, fontWeight: 700, textDecoration: "none",
              }}
            >
              Đăng nhập
            </Link>
          </div>
        )}

        {/* "Ask on a place page" note */}
        <div
          style={{
            background: "rgba(11,89,47,.05)", borderRadius: 12,
            padding: "11px 14px", marginBottom: 20,
            fontSize: 12.5, color: "var(--tm)",
          }}
        >
          💡 Để đặt câu hỏi, hãy vào trang của một địa điểm cụ thể và dùng mục{" "}
          <strong>Hỏi đáp cộng đồng</strong>.
        </div>

        {/* Questions feed */}
        {loading && questions.length === 0 && (
          <p style={{ textAlign: "center", color: "var(--tm)", padding: 40 }}>Đang tải…</p>
        )}

        {!loading && questions.length === 0 && (
          <div style={{ textAlign: "center", padding: "48px 0", color: "var(--tm)" }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🌿</div>
            <p style={{ fontSize: 14 }}>Chưa có câu hỏi nào.<br />Hãy khám phá một địa điểm và bắt đầu!</p>
            <Link
              href="/"
              style={{
                display: "inline-block", marginTop: 16,
                background: "var(--g)", color: "#fff",
                padding: "10px 22px", borderRadius: 12,
                textDecoration: "none", fontSize: 13, fontWeight: 600,
              }}
            >
              Khám phá địa điểm
            </Link>
          </div>
        )}

        {questions.map((q) => (
          <QuestionCard key={q.id} question={q} auth={auth} userId={auth?.["X-User-Id"]} />
        ))}

        {hasMore && (
          <div style={{ textAlign: "center", marginTop: 12 }}>
            <button
              onClick={() => { const next = page + 1; setPage(next); load(next, true); }}
              disabled={loading}
              style={{
                fontSize: 13, fontWeight: 600, padding: "10px 24px",
                background: "rgba(11,89,47,.08)", border: "none",
                borderRadius: 12, cursor: "pointer", color: "var(--g)",
              }}
            >
              {loading ? "Đang tải…" : "Xem thêm"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
