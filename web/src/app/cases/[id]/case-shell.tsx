"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, json } from "@/lib/api";
import { applicationNo, deadlineLabel } from "@/lib/labels";
import { TrashIcon } from "../../trash-icon";
import { translator } from "@/lib/terminology";
import { CASE_STATUS, type CaseDetail, type CaseMeta, type CaseStatus } from "@/lib/view-types";

const CaseContext = createContext<{ detail: CaseDetail; t: (value: string) => string } | null>(null);

/** The saved case, loaded once per case and shared by every tab. */
export function useCase() {
  const value = useContext(CaseContext);
  if (!value) throw new Error("useCase must be used inside CaseShell");
  return value;
}

// Line icons (24px grid, drawn with currentColor) rather than emoji: same look on every OS.
const TABS = [
  ["demo", "요약", "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"],
  ["review", "거절 이유 검토", "M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h5M14 3l5 5v3M14 3v5h5M17 17m-3 0a3 3 0 1 0 6 0a3 3 0 1 0-6 0M19.2 19.2L21 21"],
  ["claims", "청구항 현황", "M9 6h11M9 12h11M9 18h11M4 5v2M3.5 11.5h1.5l-1.5 1.5h1.5M3.5 17h1.5v2H3.5"],
  ["compare", "대응 방안", "M4 20h4L19 9l-4-4L4 16zM13.5 6.5l4 4"],
] as const;

export function CaseShell({ id, children }: { id: string; children: ReactNode }) {
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [error, setError] = useState("");
  const t = useMemo(() => translator(detail?.terms ?? {}), [detail?.terms]);

  useEffect(() => {
    api<CaseDetail>(`/cases/${id}`).then(setDetail, (e: Error) => setError(e.message));
  }, [id]);

  if (error) return <p className="page error">{error}</p>;
  if (!detail) return <p className="page muted">사건을 불러오는 중…</p>;
  return (
    <CaseContext value={{ detail, t }}>
      <CaseHeader detail={detail} onChange={(meta) => setDetail({ ...detail, case: meta })} />
      {/* Tabs run down the left; the active tab's content fills the rest. */}
      <div className="case-layout">
        <Tabs id={String(detail.case.id)} />
        <div className="case-body">{children}</div>
      </div>
    </CaseContext>
  );
}

function CaseHeader({ detail, onChange }: { detail: CaseDetail; onChange: (meta: CaseMeta) => void }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const meta = detail.case;
  const left = deadlineLabel(meta.deadline);
  // The case is named by its patent (front-page title and numbers), not a free-text name.
  const patent = (detail.result.documents.find((d) => d.kind === "patent")?.source_metadata ?? {}) as {
    title?: string;
    application_number?: string;
    publication_number?: string;
  };
  const numbers = [applicationNo(patent.application_number), patent.publication_number].filter(Boolean).join(" · ");

  function save(fields: Partial<Pick<CaseMeta, "status" | "deadline">>) {
    setError("");
    api<CaseMeta>(`/cases/${meta.id}`, json("PATCH", fields)).then(onChange, (e: Error) => setError(e.message));
  }

  async function remove() {
    if (!confirm(`'${patent.title ?? meta.title}' 사건을 삭제할까요? 분석 결과와 원본 PDF가 함께 삭제됩니다.`)) return;
    try {
      await api(`/cases/${meta.id}`, { method: "DELETE" });
      router.push("/cases");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <header className="case-header">
      <nav className="breadcrumb" aria-label="위치">
        <Link href="/cases">사건 관리</Link>
        <span aria-hidden="true">/</span>
        <span>한국 출원</span>
      </nav>
      <div className="row" style={{ justifyContent: "space-between", marginTop: 8 }}>
        <div>
          <h1 className="case-title">{patent.title ?? meta.title}</h1>
          {numbers && <div className="case-numbers">{numbers}</div>}
        </div>
        <div className="row">
          <label className="deadline-box">
            의견서 제출 기한
            <input type="date" value={meta.deadline ?? ""} onChange={(e) => save({ deadline: e.target.value || null })} />
            {meta.deadline && <span className={`left-badge${left.soon ? " soon" : ""}`}>{left.text}</span>}
          </label>
          <label className="field">
            사건 상태
            <select value={meta.status} onChange={(e) => save({ status: e.target.value as CaseStatus })}>
              {Object.entries(CASE_STATUS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="button danger icon" aria-label="사건 삭제" title="삭제" onClick={remove}>
            <TrashIcon size={18} />
          </button>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
    </header>
  );
}

function Tabs({ id }: { id: string }) {
  const pathname = usePathname();
  // Claim/scope selection travels between tabs in the URL, replacing Streamlit session jumps.
  const query = useSearchParams().toString();
  return (
    <nav className="tabs" aria-label="사건 화면">
      {TABS.map(([slug, label, icon]) => {
        const href = `/cases/${id}/${slug}`;
        return (
          <Link key={slug} href={query ? `${href}?${query}` : href} aria-current={pathname === href ? "page" : undefined}>
            <svg viewBox="0 0 24 24" width={18} height={18} fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d={icon} />
            </svg>
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
