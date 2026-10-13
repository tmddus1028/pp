"use client";

import { useState } from "react";
import { CLAIM_ROLES, claimRole, describeStatute } from "@/lib/labels";
import { useCase } from "../case-shell";

// Phase 3: port the claim detail view and improvements panel from frontend/claim_analysis.py.
export default function ClaimsPage() {
  const { detail } = useCase();
  const [filter, setFilter] = useState<string>("all");
  const rows = detail.claim_rows.map((row) => ({ row, role: claimRole(row) }));
  const shown = rows.filter((r) => filter === "all" || r.role[0] === filter);

  return (
    <section className="panel" style={{ overflow: "hidden" }} aria-labelledby="claims-title">
      <div className="panel-head">
        <div className="row" style={{ gap: 14 }}>
          <h2 id="claims-title" style={{ fontSize: 16 }}>
            청구항 {rows.length}개
          </h2>
          <div className="segmented" role="group" aria-label="청구항 거르기">
            <button type="button" aria-pressed={filter === "all"} onClick={() => setFilter("all")}>
              전체 {rows.length}
            </button>
            {CLAIM_ROLES.filter((role) => rows.some((r) => r.role === role)).map(([key, label]) => (
              <button key={key} type="button" aria-pressed={filter === key} onClick={() => setFilter(key)}>
                {label} {rows.filter((r) => r.role[0] === key).length}
              </button>
            ))}
          </div>
        </div>
        <span className="muted" style={{ fontSize: 12 }}>
          종속 관계는 청구항 문구에서 규칙으로 계산합니다
        </span>
      </div>
      <div className="table-wrap">
        <table className="table" style={{ minWidth: 760 }}>
          <thead>
            <tr>
              <th scope="col">청구항</th>
              <th scope="col">종속</th>
              <th scope="col">검토 구분</th>
              <th scope="col">거절 이유</th>
              <th scope="col">청구항 문구</th>
            </tr>
          </thead>
          <tbody>
            {shown.map(({ row, role }) => (
              <tr key={row.id} style={{ verticalAlign: "top" }}>
                <td style={{ fontWeight: 700, whiteSpace: "nowrap" }}>
                  청구항 {row.claim_number}
                </td>
                <td style={{ fontSize: 13, color: "var(--text-3)", whiteSpace: "nowrap" }}>
                  {role[0] === "canceled" ? "—" : row.depends_on?.length ? `청구항 ${row.depends_on.join(", ")}에 종속` : "독립항"}
                </td>
                <td>
                  <span className={`pill ${role[0] === "canceled" || role[0] === "other" ? "tone-plain" : role[2]}`}>{role[1]}</span>
                </td>
                <td style={{ fontSize: 13 }}>
                  {row.statutes.length
                    ? row.statutes.map((s) => {
                        const { kind, law } = describeStatute(s);
                        return (
                          <span key={s} style={{ display: "block" }}>
                            {kind} <span className="muted">· {law}</span>
                          </span>
                        );
                      })
                    : "—"}
                </td>
                <td style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-2)", maxWidth: 480 }}>{row.text}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
