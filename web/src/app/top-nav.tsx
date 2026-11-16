"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function TopNav() {
  const pathname = usePathname();
  const landing = pathname === "/";
  return (
    <header className="topbar">
      {/* On the landing page the bar lines up with the centred landing content. */}
      <div className={landing ? "topbar-inner lp-wrap" : "topbar-inner"}>
        <Link href="/" className="brand" aria-label="PINPOINT 특허 거절 대응 검토">
          {/* Same drawing as app/icon.svg (favicon): lines of text, one word highlighted, a pin on it. */}
          <svg className="brand-mark" viewBox="0 0 32 32" aria-hidden="true">
            <g fill="var(--navy)" opacity="0.3">
              <rect x="3" y="4.8" width="10" height="2.6" rx="1.3" />
              <rect x="3" y="11" width="11" height="2.6" rx="1.3" />
              <rect x="3" y="17.2" width="9.5" height="2.6" rx="1.3" />
              <rect x="3" y="23.4" width="25" height="2.6" rx="1.3" />
              <rect x="3" y="28.6" width="16" height="2.6" rx="1.3" />
            </g>
            <rect x="15.5" y="16.3" width="13" height="4.4" rx="1.4" fill="var(--accent)" />
            <path fill="var(--navy)" d="M22 16.5C20.5 14.6 16.5 11.7 16.5 8a5.5 5.5 0 0 1 11 0c0 3.7-4 6.6-5.5 8.5z" />
            <circle cx="22" cy="8" r="2.1" fill="#fff" />
          </svg>
          <span>
            <strong>
              PINP
              {/* The O is a target: ring stroke matches the letter stems, dot marks the found spot. */}
              <svg className="brand-ring" viewBox="0 0 100 100" aria-hidden="true">
                <circle cx="50" cy="50" r="41.5" fill="none" stroke="var(--accent)" strokeWidth="17" />
                <circle cx="50" cy="50" r="14" fill="var(--accent)" />
              </svg>
              INT
            </strong>
            <small>특허 거절 대응 검토</small>
          </span>
        </Link>
        {/* The landing page is for first-time visitors: its own buttons lead in, so no app menu there. */}
        {!landing && (
          <nav className="topnav" aria-label="주 메뉴">
            {/* New-case registration lives under case management (its button on /cases), so one entry covers both. */}
            <Link href="/cases" aria-current={pathname.startsWith("/cases") ? "page" : undefined}>
              사건 관리
            </Link>
          </nav>
        )}
      </div>
    </header>
  );
}
