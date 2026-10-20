"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { deadlineLabel } from "@/lib/labels";
import { CASE_STATUS, STATUS_TONE, type CaseListItem, type CaseStatus } from "@/lib/view-types";

export default function CasesPage() {
  const [cases, setCases] = useState<CaseListItem[] | null>(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState<CaseStatus | "all">("all");
  const [query, setQuery] = useState("");

  useEffect(() => {
    api<CaseListItem[]>("/cases").then(setCases, (e: Error) => setError(e.message));
  }, []);

  const all = cases ?? [];
  const q = query.trim().toLowerCase();
  const shown = all.filter(
    (c) =>
      (status === "all" || c.status === status) && (!q || c.title.toLowerCase().includes(q)),
  );
  // Open work with a deadline, nearest first.
  const due = all
    .filter((c) => c.deadline && (c.status === "open" || c.status === "in_progress"))
    .sort((a, b) => a.deadline!.localeCompare(b.deadline!))
    .slice(0, 3);
  const filters: [CaseStatus | "all", string][] = [["all", "전체"], ...(Object.entries(CASE_STATUS) as [CaseStatus, string][])];

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>사건 관리</h1>
          <p>거절 통지를 받은 출원을 제출 기한 순서로 관리합니다</p>
        </div>
        <Link href="/cases/new" className="button primary">
          새 사건 등록
        </Link>
      </header>

      {error && <p className="error">{error}</p>}

      {due.length > 0 && (
        <section aria-labelledby="due-title" className="stack" style={{ gap: 12 }}>
          <h2 id="due-title" style={{ fontSize: 16 }}>
            기한이 가까운 사건
          </h2>
          <div className="due-grid">
            {due.map((c) => {
              const left = deadlineLabel(c.deadline);
              return (
                <Link key={c.id} href={`/cases/${c.id}/review`} className="panel due-card">
                  <span className="row" style={{ justifyContent: "space-between" }}>
                    <span className={`due-left${left.soon ? " soon" : ""}`}>{left.text}</span>
                    <span className="muted" style={{ fontSize: 12 }}>
                      {c.deadline} 마감
                    </span>
                  </span>
                  <span>
                    <strong style={{ fontSize: 15 }}>{c.title}</strong>
                    <span className="muted" style={{ display: "block", fontSize: 12, marginTop: 2 }}>
                      {CASE_STATUS[c.status]}
                    </span>
                  </span>
                  <span style={{ fontSize: 13, color: "var(--text-3)" }}>
                    거절 이유 {c.rejection_count}건 · 거절된 청구항 {c.direct_count}개
                  </span>
                </Link>
              );
            })}
          </div>
        </section>
      )}

      <section aria-labelledby="all-title" className="panel" style={{ overflow: "hidden" }}>
        <div className="panel-head">
          <div className="row" style={{ gap: 14 }}>
            <h2 id="all-title" style={{ fontSize: 16 }}>
              전체 사건
            </h2>
            <div className="segmented" role="group" aria-label="사건 상태로 거르기">
              {filters.map(([value, label]) => (
                <button key={value} type="button" aria-pressed={status === value} onClick={() => setStatus(value)}>
                  {label} {value === "all" ? all.length : all.filter((c) => c.status === value).length}
                </button>
              ))}
            </div>
          </div>
          <div className="row" style={{ gap: 10 }}>
            <label className="search">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                <circle cx="11" cy="11" r="7" />
                <path d="M20 20l-3.5-3.5" />
              </svg>
              <span className="sr-only">사건 검색</span>
              <input type="search" placeholder="사건 이름으로 검색" value={query} onChange={(e) => setQuery(e.target.value)} />
            </label>
          </div>
        </div>

        {cases === null && !error && <p className="empty">불러오는 중…</p>}
        {cases?.length === 0 && (
          <p className="empty">
            아직 사건이 없습니다. <Link href="/cases/new">새 사건 등록</Link>에서 문서를 올리세요.
          </p>
        )}
        {all.length > 0 && shown.length === 0 && <p className="empty">조건에 맞는 사건이 없습니다</p>}
        {shown.length > 0 && (
          <div className="table-wrap">
            <table className="table" style={{ minWidth: 860 }}>
              <thead>
                <tr>
                  <th scope="col">사건</th>
                  <th scope="col">거절 이유</th>
                  <th scope="col">거절된 청구항</th>
                  <th scope="col">제출 기한</th>
                  <th scope="col">사건 상태</th>
                  <th scope="col">등록일</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((c) => {
                  const left = deadlineLabel(c.deadline);
                  return (
                    <tr key={c.id}>
                      <td>
                        <Link href={`/cases/${c.id}/review`} className="case-link">
                          {c.title}
                        </Link>
                      </td>
                      <td>{c.rejection_count}건</td>
                      <td style={{ fontWeight: 600, color: "var(--direct)" }}>{c.direct_count}개</td>
                      <td>
                        {c.deadline && <span style={{ fontSize: 13, marginRight: 8 }}>{c.deadline}</span>}
                        <span className={c.deadline ? `left-badge${left.soon ? " soon" : ""}` : "muted"}>{left.text}</span>
                      </td>
                      <td>
                        <span className={`pill ${STATUS_TONE[c.status]}`}>{CASE_STATUS[c.status]}</span>
                      </td>
                      <td className="muted" style={{ fontSize: 13 }}>
                        {c.created_at.slice(0, 10)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
