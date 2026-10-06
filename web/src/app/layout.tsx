import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Patent Review",
  description: "특허 거절이유 대응 관리",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko">
      <body>
        <div className="shell">
          <nav className="sidebar" aria-label="주 메뉴">
            <Link href="/cases" className="brand">
              ▤ Patent Review
            </Link>
            <Link href="/cases">사건 목록</Link>
            <Link href="/cases/new">새 사건</Link>
          </nav>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
