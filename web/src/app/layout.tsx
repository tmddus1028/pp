import type { Metadata } from "next";
import { SideNav } from "./side-nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "Patent Review",
  description: "특허 거절 대응 검토",
};

// A plain stylesheet link: next/font self-hosts the ~100 Korean subset files at build time
// and fails the whole page when one download fails. Falls back to system fonts offline.
const FONTS =
  "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap";

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko">
      <head>
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link rel="stylesheet" href={FONTS} />
      </head>
      <body>
        <div className="shell">
          <SideNav />
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
