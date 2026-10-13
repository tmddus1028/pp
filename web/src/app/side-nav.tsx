"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ICON = { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true } as const;

export function SideNav() {
  const pathname = usePathname();
  const isNew = pathname === "/cases/new";
  return (
    <nav className="sidebar" aria-label="주 메뉴">
      <Link href="/cases" className="brand">
        <span className="brand-mark">
          <svg {...ICON} width={16} height={16} strokeWidth={2}>
            <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
            <path d="M14 3v5h5M9 13h6M9 17h4" />
          </svg>
        </span>
        <span>
          <strong>Patent Review</strong>
          <small>특허 거절 대응 검토</small>
        </span>
      </Link>
      <Link href="/cases" className="nav-link" aria-current={!isNew && pathname.startsWith("/cases") ? "page" : undefined}>
        <svg {...ICON}>
          <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        </svg>
        사건 관리
      </Link>
      <Link href="/cases/new" className="nav-link" aria-current={isNew ? "page" : undefined}>
        <svg {...ICON}>
          <path d="M12 5v14M5 12h14" />
        </svg>
        새 사건 등록
      </Link>
    </nav>
  );
}
