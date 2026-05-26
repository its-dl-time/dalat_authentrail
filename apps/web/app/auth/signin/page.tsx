"use client";

import { signIn } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

function SignInContent() {
  const params    = useSearchParams();
  const callbackUrl = params.get("callbackUrl") ?? "/";

  return (
    <main
      style={{
        paddingTop: 60, minHeight: "100vh",
        display: "flex", alignItems: "center", justifyContent: "center",
      }}
    >
      <div
        style={{
          background: "#fff", borderRadius: 24,
          padding: "40px 36px", maxWidth: 400, width: "100%",
          margin: "0 16px",
          boxShadow: "0 20px 60px rgba(0,0,0,.1)",
          border: "1px solid rgba(11,89,47,.06)",
        }}
      >
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div
            style={{
              width: 56, height: 56, borderRadius: "50%",
              background: "var(--g)",
              display: "grid", placeItems: "center",
              margin: "0 auto 14px",
            }}
          >
            <svg width="26" height="26" fill="none" stroke="#fff" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/>
              <circle cx="12" cy="9" r="2.5"/>
            </svg>
          </div>
          <div style={{ fontFamily: "Unbounded, sans-serif", fontSize: 18, fontWeight: 700, color: "var(--g)" }}>
            DaLat Authentrail
          </div>
          <div style={{ fontSize: 12.5, color: "var(--tm)", marginTop: 6 }}>
            Đăng nhập để tham gia cộng đồng
          </div>
        </div>

        {/* Google sign-in button */}
        <button
          onClick={() => signIn("google", { callbackUrl })}
          style={{
            width: "100%",
            display: "flex", alignItems: "center", justifyContent: "center", gap: 12,
            background: "#fff", color: "#333",
            border: "2px solid rgba(0,0,0,.12)",
            borderRadius: 12, padding: "13px 20px",
            fontSize: 14, fontWeight: 600, cursor: "pointer",
            transition: ".2s",
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = "#f5f5f5"; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = "#fff"; }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Tiếp tục với Google
        </button>

        <p style={{ textAlign: "center", fontSize: 11, color: "var(--tm)", marginTop: 20, lineHeight: 1.6 }}>
          Bằng cách đăng nhập, bạn đồng ý với điều khoản sử dụng
          và chính sách bảo mật của DaLat Authentrail.
        </p>
      </div>
    </main>
  );
}

export default function SignInPage() {
  return (
    <Suspense>
      <SignInContent />
    </Suspense>
  );
}
