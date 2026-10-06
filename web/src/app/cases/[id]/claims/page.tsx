"use client";

import { useCase } from "../case-shell";

// Phase 3: port frontend/claim_analysis.py (filters, detail view, improvements panel).
export default function ClaimsPage() {
  const { detail, t } = useCase();
  return (
    <table className="table">
      <thead>
        <tr>
          <th>{t("Claim")}</th>
          <th>상태</th>
          <th>{t("거절 사유")}</th>
        </tr>
      </thead>
      <tbody>
        {detail.claim_rows.map((row) => (
          <tr key={row.id}>
            <td>{t(row.title)}</td>
            <td>
              <span className={`badge role-${row.role}`}>{t(row.label)}</span>
            </td>
            <td>{row.statutes.join(", ") || "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
