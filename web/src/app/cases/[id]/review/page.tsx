"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { CITATION_ROLE, CLAIM_ROLES, claimRole, describeStatute, documentLabel } from "@/lib/labels";
import type { AnalysisResult, Annotation, ReviewModel, ViewItem } from "@/lib/view-types";
import { useCase } from "../case-shell";

type Doc = ReviewModel["documents"][number];
type Page = Doc["pages"][number];
/** Which document to show and what to scroll to; nonce re-runs the scroll for the same target. */
type Focus = { doc: string; claim?: number; nonce: number };

const MARK: Record<string, string> = {
  direct_rejection: "mark-direct",
  dependency: "mark-dependency",
  citation: "mark-citation",
  specification: "mark-specification",
};
// Overlapping highlights: the narrower, more specific mark wins.
const PRIORITY = ["citation", "specification", "dependency", "direct_rejection"];

export default function ReviewPage() {
  const { detail } = useCase();
  const { review, result, case: meta } = detail;
  const korean = meta.jurisdiction === "KR";
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
          korean={korean}
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
            korean={korean}
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

function DocumentViewer({
  caseId,
  docs,
  korean,
  focus,
  marks,
  onDoc,
}: {
  caseId: number;
  docs: Doc[];
  korean: boolean;
  focus: Focus;
  marks: Annotation[];
  onDoc: (id: string) => void;
}) {
  const doc = docs.find((d) => d.id === focus.doc) ?? docs[0];
  const isPdf = !!doc?.filename.toLowerCase().endsWith(".pdf");
  const [textMode, setTextMode] = useState(false);
  const stage = useRef<HTMLDivElement>(null);
  const docMarks = marks.filter((m) => m.document_id === doc?.id);
  const asImage = isPdf && !textMode;

  useEffect(() => {
    const box = stage.current;
    const target = box?.querySelector(focus.claim ? `[data-claim="${focus.claim}"]` : "[data-hit]");
    if (!box) return;
    box.scrollTop = target ? box.scrollTop + target.getBoundingClientRect().top - box.getBoundingClientRect().top - 80 : 0;
  }, [focus, asImage]);

  if (!doc) return <section className="panel col-doc empty">표시할 문서가 없습니다</section>;
  const label = documentLabel(doc.kind, korean, doc.filename);

  return (
    <section className="panel col-doc" aria-label="원문">
      <div className="doc-toolbar">
        <div className="segmented" role="tablist" aria-label="문서 선택">
          {docs.map((d) => (
            <button key={d.id} type="button" role="tab" aria-selected={d.id === doc.id} onClick={() => onDoc(d.id)}>
              {documentLabel(d.kind, korean, d.filename)}
            </button>
          ))}
        </div>
        <div className="row" style={{ gap: 8, fontSize: 13, color: "var(--text-3)" }}>
          {isPdf && (
            <div className="segmented" role="group" aria-label="보기 방식">
              <button type="button" aria-pressed={!textMode} onClick={() => setTextMode(false)}>
                원본 페이지
              </button>
              <button type="button" aria-pressed={textMode} onClick={() => setTextMode(true)}>
                추출 텍스트
              </button>
            </div>
          )}
          <span>{doc.pages.length}쪽</span>
          {isPdf && (
            <a href={`/api/cases/${caseId}/files/${doc.id}`} target="_blank" rel="noreferrer">
              PDF 열기
            </a>
          )}
        </div>
      </div>
      <div className="doc-legend legend-row">
        <span>
          <span className="swatch mark mark-direct" />
          심사관이 거절한 부분
        </span>
        <span>
          <span className="swatch mark mark-citation" />
          선행문헌 언급
        </span>
        <span>
          <span className="swatch mark mark-dependency" />
          함께 검토할 종속항
        </span>
        <span style={{ marginLeft: "auto" }}>
          {docMarks.length ? "원문은 수정하지 않고 그대로 보여줍니다" : "이 문서에는 선택한 거절 이유의 표시가 없습니다"}
        </span>
      </div>
      <div className="doc-stage" ref={stage}>
        {doc.pages.map((page) => (
          <div key={page.number} className="stack" style={{ gap: 14 }}>
            <span className="sheet-label">{page.number}쪽</span>
            {asImage ? (
              <ImagePage caseId={caseId} doc={doc} page={page} label={label} marks={docMarks} onFail={() => setTextMode(true)} />
            ) : (
              <div className="sheet sheet-text">
                {segments(page, docMarks).map((s, i) =>
                  s.mark ? (
                    <mark key={i} className={MARK[s.mark.type]} data-hit="" data-claim={s.mark.claim_number ?? undefined}>
                      {s.text}
                    </mark>
                  ) : (
                    s.text
                  ),
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function ImagePage({
  caseId,
  doc,
  page,
  label,
  marks,
  onFail,
}: {
  caseId: number;
  doc: Doc;
  page: Page;
  label: string;
  marks: Annotation[];
  onFail: () => void;
}) {
  return (
    <div className="sheet sheet-image">
      {/* eslint-disable-next-line @next/next/no-img-element -- backend-rendered page, not a static asset */}
      <img
        src={`/api/cases/${caseId}/files/${doc.id}/pages/${page.number}`}
        alt={`${label} ${page.number}쪽`}
        loading="lazy"
        style={{ aspectRatio: "210 / 297" }}
        onLoad={(e) => {
          const img = e.currentTarget;
          img.style.aspectRatio = `${img.naturalWidth} / ${img.naturalHeight}`;
        }}
        onError={onFail}
      />
      {marks
        .filter((m) => m.page === page.number)
        .flatMap((m) =>
          m.boxes.map(([x0, y0, x1, y1], i) => (
            <span
              key={`${m.id}-${i}`}
              className={`box ${MARK[m.type]}`}
              data-hit=""
              data-claim={m.claim_number ?? undefined}
              style={{ left: `${x0 * 100}%`, top: `${y0 * 100}%`, width: `${(x1 - x0) * 100}%`, height: `${(y1 - y0) * 100}%` }}
            />
          )),
        )}
    </div>
  );
}

/** Split a page's text at highlight edges; offsets in annotations are document-wide. */
function segments(page: Page, marks: Annotation[]) {
  const local = marks
    .map((m) => ({ m, from: Math.max(0, m.start - page.start), to: Math.min(page.text.length, m.end - page.start) }))
    .filter((x) => x.from < x.to);
  const cuts = [...new Set([0, page.text.length, ...local.flatMap((x) => [x.from, x.to])])].sort((a, b) => a - b);
  return cuts.slice(0, -1).map((from, i) => {
    const to = cuts[i + 1];
    const cover = local
      .filter((x) => x.from <= from && x.to >= to)
      .sort((a, b) => PRIORITY.indexOf(a.m.type) - PRIORITY.indexOf(b.m.type));
    return { text: page.text.slice(from, to), mark: cover[0]?.m };
  });
}

function RejectionDetail({
  rejection,
  index,
  total,
  impact,
  claims,
  annotations,
  docs,
  korean,
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
  korean: boolean;
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
            {evidenceDoc ? documentLabel(evidenceDoc.kind, korean, evidenceDoc.filename) : "통지서"} ·{" "}
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
