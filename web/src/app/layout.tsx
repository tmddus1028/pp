import type { Metadata } from "next";
import { TopNav } from "./top-nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "PinPoint",
  description: "특허 거절 대응 검토",
};

// One font for everything. A plain stylesheet link: next/font self-hosts the ~100 Korean subset
// files at build time and fails the whole page when one download fails. Falls back to system fonts offline.
const PRETENDARD =
  "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css";

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko">
      <head>
        <link rel="preconnect" href="https://cdn.jsdelivr.net" crossOrigin="" />
        <link rel="stylesheet" href={PRETENDARD} />
      </head>
      <body>
        <div className="shell">
          <TopNav />
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
