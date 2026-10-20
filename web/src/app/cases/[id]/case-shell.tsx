"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, json } from "@/lib/api";
import { deadlineLabel } from "@/lib/labels";
import { translator } from "@/lib/terminology";
import { CASE_STATUS, type CaseDetail, type CaseMeta, type CaseStatus } from "@/lib/view-types";

const CaseContext = createContext<{ detail: CaseDetail; t: (value: string) => string } | null>(null);

/** The saved case, loaded once per case and shared by every tab. */
export function useCase() {
  const value = useContext(CaseContext);
  if (!value) throw new Error("useCase must be used inside CaseShell");
  return value;
}

const TABS = [
  ["review", "거절 이유 검토"],
  ["claims", "청구항 현황"],
  ["map", "관계도"],
  ["compare", "대응 방안"],
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
      <CaseHeader meta={detail.case} onChange={(meta) => setDetail({ ...detail, case: meta })} />
      <div className="case-body">{children}</div>
    </CaseContext>
  );
}

function CaseHeader({ meta, onChange }: { meta: CaseMeta; onChange: (meta: CaseMeta) => void }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const left = deadlineLabel(meta.deadline);

  function save(fields: Partial<Pick<CaseMeta, "title" | "status" | "deadline">>) {
    setError("");
    api<CaseMeta>(`/cases/${meta.id}`, json("PATCH", fields)).then(onChange, (e: Error) => setError(e.message));
  }

  async function remove() {
    if (!confirm(`'${meta.title}' 사건을 삭제할까요? 분석 결과와 원본 PDF가 함께 삭제됩니다.`)) return;
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
        <input
          className="title-input"
          aria-label="사건 이름"
          defaultValue={meta.title}
          maxLength={200}
          onBlur={(e) => {
            const title = e.target.value.trim();
            if (title && title !== meta.title) save({ title });
          }}
          onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
        />
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
          <button type="button" className="button danger" onClick={remove}>
            삭제
          </button>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      <Tabs id={String(meta.id)} />
    </header>
  );
}

function Tabs({ id }: { id: string }) {
  const pathname = usePathname();
  // Claim/scope selection travels between tabs in the URL, replacing Streamlit session jumps.
  const query = useSearchParams().toString();
  return (
    <nav className="tabs" aria-label="사건 화면">
      {TABS.map(([slug, label]) => {
        const href = `/cases/${id}/${slug}`;
        return (
          <Link key={slug} href={query ? `${href}?${query}` : href} aria-current={pathname === href ? "page" : undefined}>
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
