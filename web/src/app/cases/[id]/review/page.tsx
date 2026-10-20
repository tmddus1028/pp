"use client";

import Link from "next/link";
import { useState } from "react";
import { CITATION_ROLE, CLAIM_ROLES, claimRole, describeStatute, documentLabel } from "@/lib/labels";
import type { AnalysisResult, Annotation, ReviewModel, ViewItem } from "@/lib/view-types";
import { useCase } from "../case-shell";
import { DocumentViewer, MARK, type Doc, type Focus } from "../document-viewer";

export default function ReviewPage() {
  const { detail } = useCase();
  const { review, result, case: meta } = detail;
  const rejections = review.rejections;
  const [selected, setSelected] = useState(rejections[0]?.rejection_id ?? "");
  const [focus, setFocus] = useState<Focus>({
    doc: rejections[0]?.evidence.document_id || review.documents[0]?.id || "",
    nonce: 0,
  });
  const show = (doc: string, claim?: number) => setFocus((f) => ({ doc, claim, nonce: f.nonce + 1 }));

  const rejection = rejections.find((r) => r.rejection_id === selected);
  const impact = review.impacts.find((i) => i.rejection_id === selected);
  // A claim annotation carries its role across all rejections; recolor it for the selected one.
  const marks = review.annotations
    .filter((a) => MARK[a.type] && (a.linked_rejection_id === selected || a.linked_rejection_ids.includes(selected)))
    .map((a) =>
      a.claim_number != null && impact?.dependency_impacted_claims.includes(a.claim_number)
        ? { ...a, type: "dependency" as const }
        : a,
    );
  const warnings = [...new Set(review.warnings)];

  function pick(id: string) {
    setSelected(id);
    const doc = rejections.find((r) => r.rejection_id === id)?.evidence.document_id;
    if (doc) show(doc);
  }

  return (
    <div className="stack">
      {warnings.length > 0 && (
        <details className="notice">
          <summary>분석 참고 사항 {warnings.length}건 · 결과를 쓰기 전에 확인하세요</summary>
          <ul>
            {warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </details>
      )}
      <div className="workspace">
        <section className="col-list" aria-label="거절 이유 목록">
          <RejectionList rejections={rejections} impacts={review.impacts} selected={selected} onPick={pick} />
          <ClaimOverview claims={review.items.filter((i) => i.kind === "claim")} />
        </section>
        <DocumentViewer
          caseId={meta.id}
          docs={review.documents}
          focus={focus}
          marks={marks}
          onDoc={(doc) => show(doc)}
        />
        {rejection ? (
          <RejectionDetail
            key={rejection.rejection_id}
            rejection={rejection}
            index={rejections.indexOf(rejection) + 1}
            total={rejections.length}
            impact={impact}
            claims={review.items}
            annotations={review.annotations}
            docs={review.documents}
            result={result}
            caseId={meta.id}
            onShow={show}
          />
        ) : (
          <aside className="panel col-detail">
            <p className="muted" style={{ margin: 0 }}>
              추출된 거절 이유가 없습니다. 거절이 없다는 뜻은 아니므로 통지서 원문을 직접 확인하세요.
            </p>
          </aside>
        )}
      </div>
    </div>
  );
}

function RejectionList({
  rejections,
  impacts,
  selected,
  onPick,
}: {
  rejections: ReviewModel["rejections"];
  impacts: ReviewModel["impacts"];
  selected: string;
  onPick: (id: string) => void;
}) {
  return (
    <div className="panel panel-pad">
      <h2 className="section-title" style={{ marginBottom: 12 }}>
        거절 이유 {rejections.length}건
      </h2>
      <div className="stack" style={{ gap: 8 }}>
        {rejections.map((r, i) => {
          const { kind, law } = describeStatute(r.statute, r.action_type === "objection");
          const claims = impacts.find((x) => x.rejection_id === r.rejection_id)?.direct_claims ?? r.claims;
          return (
            <button
              key={r.rejection_id}
              type="button"
              className="rej-item"
              aria-pressed={r.rejection_id === selected}
              onClick={() => onPick(r.rejection_id)}
            >
              <span className="muted" style={{ fontSize: 12 }}>
                거절 이유 {i + 1}
              </span>
              <span className="kind">{kind}</span>
              <span className="meta">
                {law} · 청구항 {claims.join(", ") || "확인 필요"}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function ClaimOverview({ claims }: { claims: ViewItem[] }) {
  if (!claims.length) return null;
  const roles = claims.map(claimRole);
  return (
    <div className="panel panel-pad">
      <h2 className="section-title" style={{ marginBottom: 12 }}>
        청구항 {claims.length}개 현황
      </h2>
      <div className="claim-grid">
        {claims.map((c, i) => {
          const role = roles[i];
          return (
            <div key={c.id} className={`claim-cell ${role[2]}`} title={`청구항 ${c.claim_number} · ${role[1]}`}>
              {c.claim_number}
            </div>
          );
        })}
      </div>
      <ul className="legend">
        {CLAIM_ROLES.filter((role) => roles.includes(role)).map(([key, label, tone]) => (
          <li key={key}>
            <span className={`swatch claim-cell ${tone}`} style={{ height: 10 }} />
            {label} {roles.filter((r) => r[0] === key).length}개
          </li>
        ))}
      </ul>
    </div>
  );
}

function RejectionDetail({
  rejection,
  index,
  total,
  impact,
  claims,
  annotations,
  docs,
  result,
  caseId,
  onShow,
}: {
  rejection: ReviewModel["rejections"][number];
  index: number;
  total: number;
  impact: ReviewModel["impacts"][number] | undefined;
  claims: ViewItem[];
  annotations: Annotation[];
  docs: Doc[];
  result: AnalysisResult;
  caseId: number;
  onShow: (doc: string, claim?: number) => void;
}) {
  const { kind, law } = describeStatute(rejection.statute, rejection.action_type === "objection");
  const evidenceDoc = docs.find((d) => d.id === rejection.evidence.document_id);
  const direct = impact?.direct_claims ?? rejection.claims;
  const deps = impact?.dependency_impacted_claims ?? [];
  const claimDoc = (n: number) => annotations.find((a) => a.claim_number === n && a.item_id === `claim-${n}`)?.document_id;

  const claimChip = (n: number, tone: string) => {
    const doc = claimDoc(n);
    return doc ? (
      <button key={n} type="button" className={`chip ${tone}`} style={{ border: 0, cursor: "pointer" }} onClick={() => onShow(doc, n)}>
        청구항 {n}
      </button>
    ) : (
      <span key={n} className={`chip ${tone}`}>
        청구항 {n}
      </span>
    );
  };

  return (
    <aside className="panel col-detail" aria-label="거절 이유 상세">
      <div>
        <div className="muted" style={{ fontSize: 12 }}>
          거절 이유 {index} / {total}
        </div>
        <h2 style={{ fontSize: 20, marginTop: 4 }}>{kind}</h2>
        <div style={{ marginTop: 4, fontSize: 13, color: "var(--text-3)" }}>{law}</div>
      </div>

      <div className="evidence">
        <div className="evidence-title">심사관 지적 원문</div>
        <p>{rejection.evidence.text}</p>
        <div className="evidence-foot">
          <span>
            {evidenceDoc ? documentLabel(evidenceDoc.kind, evidenceDoc.filename) : "통지서"} ·{" "}
            {rejection.evidence.page_numbers.join(", ")}쪽
          </span>
          {evidenceDoc && (
            <button type="button" className="link-button" onClick={() => onShow(evidenceDoc.id)}>
              원문에서 위치 보기
            </button>
          )}
        </div>
      </div>

      <div>
        <h3 className="label">거절된 청구항</h3>
        <div className="chips">
          {direct.map((n) => claimChip(n, "tone-direct"))}
          {!direct.length && <span className="muted" style={{ fontSize: 13 }}>확인 필요</span>}
        </div>
      </div>

      {!!impact?.objected_claims?.length && (
        <div>
          <h3 className="label">형식 지적 청구항</h3>
          <div className="chips">
            {impact.objected_claims.map((n) => claimChip(n, "tone-info"))}
          </div>
        </div>
      )}

      <div>
        <h3 className="label" style={{ marginBottom: 4 }}>
          함께 검토할 종속항
        </h3>
        <p className="hint">거절된 청구항에 종속되어 같은 거절 이유가 미칩니다</p>
        {deps.length ? (
          <ul className="dep-list">
            {deps.map((n) => {
              const parents = claims.find((c) => c.claim_number === n)?.depends_on ?? [];
              return (
                <li key={n}>
                  {claimChip(n, "tone-dep")}
                  {parents.length > 0 && <span>청구항 {parents.join(", ")}에 종속</span>}
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="muted" style={{ margin: 0, fontSize: 13 }}>
            해당 종속항 없음
          </p>
        )}
      </div>

      {!!impact?.missing_claims.length && (
        <p className="notice">
          청구항 문서에서 찾지 못한 청구항 · {impact.missing_claims.join(", ")} · 통지서 당시 청구항 버전을 확인하세요
        </p>
      )}

      <div>
        <h3 className="label">인용 선행문헌</h3>
        {rejection.cited_references.length ? (
          <div className="stack" style={{ gap: 8 }}>
            {rejection.cited_references.map((ref) => {
              const role =
                result.rejection_citations?.find(
                  (c) => c.rejection_id === rejection.rejection_id && c.citation_id === ref.citation_id,
                )?.role ?? "relied_upon";
              const source = result.citations?.find((c) => c.citation_id === ref.citation_id)?.source_document_id;
              return (
                <div key={ref.citation_id} className="ref-card">
                  <div className="top">
                    <span className="name">{ref.name || ref.title || ref.raw_text}</span>
                    <span className="pill tone-cite">{CITATION_ROLE[role] ?? role}</span>
                  </div>
                  {ref.publication_number && (
                    <span className="mono" style={{ fontSize: 12, color: "var(--text-3)" }}>
                      {ref.publication_number}
                    </span>
                  )}
                  <div className="foot">
                    {source && docs.some((d) => d.id === source) ? (
                      <button type="button" className="link-button" onClick={() => onShow(source)}>
                        선행문헌 원문 보기
                      </button>
                    ) : (
                      <span className="missing">원문 미확보 · 새 사건 등록 때 원문을 함께 올리면 연결됩니다</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="muted" style={{ margin: 0, fontSize: 13 }}>
            인용 문헌 없음
          </p>
        )}
      </div>

      <div className="detail-actions">
        <Link className="button" href={`/cases/${caseId}/compare${direct[0] ? `?claim=${direct[0]}` : ""}`}>
          선행문헌 대비하기
        </Link>
        <Link className="button" href={`/cases/${caseId}/claims`}>
          청구항 현황 보기
        </Link>
      </div>
    </aside>
  );
}
