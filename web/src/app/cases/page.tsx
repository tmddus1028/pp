"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { applicationNo, deadlineLabel, describeStatute } from "@/lib/labels";
import { CASE_STATUS, STATUS_TONE, type CaseListItem, type CaseStatus } from "@/lib/view-types";
import { TrashIcon } from "../trash-icon";
import { NewCaseForm } from "./new-case-form";

export default function CasesPage() {
  const router = useRouter();
  const [cases, setCases] = useState<CaseListItem[] | null>(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState<CaseStatus | "all">("all");
  const [query, setQuery] = useState("");

  // Registration is a native dialog over the list, opened only by the 새 사건 등록 button.
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    api<CaseListItem[]>("/cases").then(setCases, (e: Error) => setError(e.message));
  }, []);

  const all = cases ?? [];
  const q = query.trim().toLowerCase().replaceAll("-", "");
  // The server already orders by nearest deadline, then newest (backend/store.py list_cases).
  const shown = all.filter(
    (c) =>
      (status === "all" || c.status === status) &&
      (!q || [c.title, c.application_number, c.invention_title].some((v) => v?.toLowerCase().replaceAll("-", "").includes(q))),
  );
  const filters: [CaseStatus | "all", string][] = [["all", "전체"], ...(Object.entries(CASE_STATUS) as [CaseStatus, string][])];

  async function remove(c: CaseListItem) {
    const name = c.invention_title ?? c.title;
    if (!confirm(`'${name}' 사건을 삭제할까요? 분석 결과와 원본 PDF가 함께 삭제됩니다.`)) return;
    try {
      await api(`/cases/${c.id}`, { method: "DELETE" });
      setCases((list) => list?.filter((x) => x.id !== c.id) ?? null);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="page">
      {/* No page title: the top bar's 사건 관리 already says where we are. */}
      <h1 className="sr-only">사건 관리</h1>

      <dialog ref={dialog} className="modal" aria-labelledby="new-case-title">
        <div className="modal-head">
          <h2 id="new-case-title">새 사건 등록</h2>
          <button type="button" className="modal-close" aria-label="닫기" onClick={() => dialog.current?.close()}>
            ×
          </button>
        </div>
        <NewCaseForm />
      </dialog>

      {error && <p className="error">{error}</p>}

      <section aria-label="사건 목록" className="panel" style={{ overflow: "hidden" }}>
        <div className="panel-head">
          <div className="row" style={{ gap: 14 }}>
            <div className="segmented" role="group" aria-label="사건 상태로 거르기">
              {filters.map(([value, label]) => (
                <button key={value} type="button" aria-pressed={status === value} onClick={() => setStatus(value)}>
                  {label} {value === "all" ? all.length : all.filter((c) => c.status === value).length}
                </button>
              ))}
            </div>
            <span className="muted" style={{ fontSize: 13 }}>
              {shown.length}건
            </span>
          </div>
          <div className="row" style={{ gap: 10 }}>
            <label className="search">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                <circle cx="11" cy="11" r="7" />
                <path d="M20 20l-3.5-3.5" />
              </svg>
              <span className="sr-only">사건 검색</span>
              <input
                type="search"
                placeholder="출원번호 · 발명의 명칭"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
            <button type="button" className="button primary" onClick={() => dialog.current?.showModal()}>
              새 사건 등록
            </button>
          </div>
        </div>

        {cases === null && !error && <p className="empty">불러오는 중…</p>}
        {cases?.length === 0 && (
          <p className="empty">
            아직 사건이 없습니다.{" "}
            <button type="button" className="link-button" style={{ fontSize: "inherit" }} onClick={() => dialog.current?.showModal()}>
              새 사건 등록
            </button>
            에서 문서를 올리세요.
          </p>
        )}
        {all.length > 0 && shown.length === 0 && <p className="empty">조건에 맞는 사건이 없습니다</p>}
        {shown.length > 0 && (
          <div className="table-wrap">
            <table className="table grid case-table">
              <thead>
                <tr>
                  <th scope="col" className="c-num">번호</th>
                  <th scope="col" className="c-app">출원번호</th>
                  <th scope="col">발명의 명칭</th>
                  <th scope="col" className="c-reason">거절 이유</th>
                  <th scope="col" className="c-claims">거절 청구항</th>
                  <th scope="col" className="c-date">통지일</th>
                  <th scope="col" className="c-due">제출 기한</th>
                  <th scope="col" className="c-status">상태</th>
                  <th scope="col" className="c-action">
                    <span className="sr-only">관리</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {shown.map((c, i) => {
                  const left = deadlineLabel(c.deadline);
                  const href = `/cases/${c.id}/demo`;
                  return (
                    // The whole row opens the case; the title stays a real link for keyboard and screen readers.
                    <tr key={c.id} onClick={() => router.push(href)}>
                      <td className="c-num">{shown.length - i}</td>
                      <td className="c-app">{applicationNo(c.application_number)}</td>
                      <td className="clip" title={c.invention_title ?? c.title}>
                        <Link href={href} className="case-link" onClick={(e) => e.stopPropagation()}>
                          {c.invention_title ?? c.title}
                        </Link>
                      </td>
                      <td className="c-reason clip">
                        {c.statutes.map((s) => describeStatute(s).kind).join(", ") || "—"}
                      </td>
                      <td className="c-claims">{c.direct_claims.join(", ") || "—"}</td>
                      <td className="c-date">{c.notice_date ?? "—"}</td>
                      <td className="c-due">
                        {c.deadline ? (
                          <span className={`left-badge${left.soon ? " soon" : ""}`} title={c.deadline}>
                            {left.text}
                          </span>
                        ) : (
                          <span className="muted">—</span>
                        )}
                      </td>
                      <td className="c-status">
                        <span className={`pill ${STATUS_TONE[c.status]}`}>{CASE_STATUS[c.status]}</span>
                      </td>
                      <td className="c-action">
                        <button
                          type="button"
                          className="row-delete"
                          aria-label={`${c.invention_title ?? c.title} 삭제`}
                          title="삭제"
                          onClick={(e) => {
                            e.stopPropagation(); // the row itself opens the case
                            remove(c);
                          }}
                        >
                          <TrashIcon />
                        </button>
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
