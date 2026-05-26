import type { Metadata } from "next";
import { Geist, Unbounded } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/nav/Navbar";
import SessionProvider from "@/components/providers/SessionProvider";

const geist = Geist({
  variable: "--font-geist",
  subsets: ["latin"],
  display: "swap",
});

const unbounded = Unbounded({
  variable: "--font-unbounded",
  subsets: ["latin"],
  weight: ["400", "600", "700", "900"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "DaLat Authentrail",
  description:
    "Khám phá địa điểm Đà Lạt với độ tin cậy được đánh giá từ nhiều nguồn: Google Maps, Facebook và TikTok.",
  keywords: ["Đà Lạt", "du lịch", "địa điểm", "đánh giá", "trust score"],
  openGraph: {
    title: "DaLat Authentrail",
    description: "Địa điểm nào thực sự đáng tin ở Đà Lạt?",
    locale: "vi_VN",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi" className={`${geist.variable} ${unbounded.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-cream text-[var(--tx)]">
        <SessionProvider>
          <Navbar />
          {children}
        </SessionProvider>
      </body>
    </html>
  );
}
