"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { CASE_STATUS, type CaseListItem, type CaseStatus } from "@/lib/view-types";

function dday(deadline: string | null) {
  if (!deadline) return "";
  const days = Math.round((Date.parse(deadline) - Date.parse(new Date().toISOString().slice(0, 10))) / 86_400_000);
  return days === 0 ? "D-day" : days > 0 ? `D-${days}` : `D+${-days}`;
}

export default function CasesPage() {
  const router = useRouter();
  const [cases, setCases] = useState<CaseListItem[] | null>(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState<CaseStatus | "all">("all");

  useEffect(() => {
    api<CaseListItem[]>("/cases").then(setCases, (e: Error) => setError(e.message));
  }, []);

  const shown = cases?.filter((c) => status === "all" || c.status === status) ?? [];

  return (
    <>
      <header className="page-header">
        <h1>사건 목록</h1>
        <Link href="/cases/new" className="button primary">
          새 사건
        </Link>
      </header>
      <div className="toolbar">
        <label>
          상태{" "}
          <select value={status} onChange={(e) => setStatus(e.target.value as CaseStatus | "all")}>
            <option value="all">전체</option>
            {Object.entries(CASE_STATUS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      {cases === null && !error && <p className="muted">불러오는 중…</p>}
      {cases?.length === 0 && (
        <p className="muted">
          아직 사건이 없습니다. <Link href="/cases/new">새 사건</Link>에서 문서를 업로드하세요.
        </p>
      )}
      {shown.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>사건</th>
              <th>관할</th>
              <th>거절 사유</th>
              <th>직접 지적 청구항</th>
              <th>상태</th>
              <th>마감일</th>
              <th>등록일</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((c) => (
              <tr key={c.id} className="clickable" onClick={() => router.push(`/cases/${c.id}/review`)}>
                <td>
                  <Link href={`/cases/${c.id}/review`} onClick={(e) => e.stopPropagation()}>
                    {c.title}
                  </Link>
                </td>
                <td>{c.jurisdiction === "KR" ? "한국" : "미국"}</td>
                <td>{c.rejection_count}</td>
                <td>{c.direct_count}</td>
                <td>
                  <span className={`badge status-${c.status}`}>{CASE_STATUS[c.status]}</span>
                </td>
                <td>
                  {c.deadline ?? "—"} <span className="muted">{dday(c.deadline)}</span>
                </td>
                <td>{c.created_at.slice(0, 10)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
