"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";

const LINKS = [
  { href: "/",          label: "Khám phá"  },
  { href: "/community", label: "Cộng đồng" },
];

export default function Navbar() {
  const path          = usePathname();
  const { data: sess, status } = useSession();

  return (
    <nav
      style={{
        position: "fixed", top: 0, left: 0, right: 0,
        zIndex: 200,
        background: "rgba(240,231,215,.97)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid rgba(11,89,47,.1)",
        height: 60,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 28px",
      }}
    >
      {/* Logo */}
      <Link href="/" style={{ display: "flex", alignItems: "center", gap: 9, textDecoration: "none" }}>
        <div
          style={{
            width: 34, height: 34, background: "var(--g)",
            borderRadius: "50%", display: "grid", placeItems: "center",
          }}
        >
          <svg width="18" height="18" fill="none" stroke="#fff" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/>
            <circle cx="12" cy="9" r="2.5"/>
          </svg>
        </div>
        <div style={{ fontFamily: "Unbounded, sans-serif", fontSize: 12, fontWeight: 700, color: "var(--g)", lineHeight: 1.2 }}>
          Authentrail
          <span style={{ display: "block", fontSize: 9, fontWeight: 400, color: "var(--o)", letterSpacing: 2, textTransform: "uppercase" }}>
            Đà Lạt
          </span>
        </div>
      </Link>

      {/* Nav links + right side */}
      <div style={{ display: "flex", gap: 3, alignItems: "center" }}>
        {LINKS.map((link) => {
          const active = link.href === "/" ? path === "/" : path.startsWith(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              style={{
                background: active ? "var(--g)" : "none",
                color: active ? "#fff" : "var(--tm)",
                padding: "7px 13px", borderRadius: 18,
                fontSize: 12.5, fontWeight: 500,
                textDecoration: "none", transition: ".2s",
              }}
            >
              {link.label}
            </Link>
          );
        })}

        {/* Auth: loading → nothing | logged in → avatar | logged out → button */}
        {status === "loading" && <div style={{ width: 32, height: 32 }} />}

        {status === "authenticated" && sess?.user && (
          <button
            onClick={() => signOut()}
            title={`Đăng xuất (${sess.user?.name ?? ""})`}
            style={{
              display: "flex", alignItems: "center", gap: 10,
              cursor: "pointer", padding: "4px 8px",
              borderRadius: 20, background: "none", border: "none",
              transition: ".2s", marginLeft: 4,
            }}
          >
            {sess.user.image ? (
              <Image
                src={sess.user.image}
                alt={sess.user.name ?? ""}
                width={32} height={32}
                style={{ borderRadius: "50%", border: "2px solid var(--l)" }}
              />
            ) : (
              <div
                style={{
                  width: 32, height: 32, background: "var(--g)",
                  borderRadius: "50%", display: "grid", placeItems: "center",
                  color: "#fff", fontSize: 12, fontWeight: 700,
                  border: "2px solid var(--l)",
                }}
              >
                {(sess.user.name ?? "?")[0].toUpperCase()}
              </div>
            )}
            <div style={{ textAlign: "left" }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--tx)" }}>{sess.user.name}</div>
              <div style={{ fontSize: 10, color: "var(--g)", fontWeight: 600 }}>Thành viên</div>
            </div>
          </button>
        )}

        {status === "unauthenticated" && (
          <Link
            href="/auth/signin"
            style={{
              background: "var(--g)", color: "#fff",
              border: "none", padding: "7px 16px",
              borderRadius: 18, fontSize: 12.5, fontWeight: 600,
              textDecoration: "none", transition: ".2s", marginLeft: 4,
            }}
          >
            Đăng nhập
          </Link>
        )}
      </div>
    </nav>
  );
}
