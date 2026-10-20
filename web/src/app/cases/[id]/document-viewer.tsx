"use client";

import { useEffect, useRef, useState } from "react";
import { documentLabel } from "@/lib/labels";
import type { Annotation, ReviewModel } from "@/lib/view-types";

export type Doc = ReviewModel["documents"][number];
type Page = Doc["pages"][number];
/** Which document to show and what to scroll to; nonce re-runs the scroll for the same target. */
export type Focus = { doc: string; claim?: number; nonce: number };

export const MARK: Record<string, string> = {
  direct_rejection: "mark-direct",
  dependency: "mark-dependency",
  citation: "mark-citation",
  specification: "mark-specification",
};
// Overlapping highlights: the narrower, more specific mark wins.
const PRIORITY = ["citation", "specification", "dependency", "direct_rejection"];

export function DocumentViewer({
  caseId,
  docs,
  focus,
  marks,
  onDoc,
  emptyNote = "이 문서에는 선택한 거절 이유의 표시가 없습니다",
  textFirst = false,
}: {
  caseId: number;
  docs: Doc[];
  focus: Focus;
  marks: Annotation[];
  onDoc: (id: string) => void;
  emptyNote?: string;
  /** Start in extracted-text mode, for marks that have no page boxes. */
  textFirst?: boolean;
}) {
  const doc = docs.find((d) => d.id === focus.doc) ?? docs[0];
  const isPdf = !!doc?.filename.toLowerCase().endsWith(".pdf");
  const [textMode, setTextMode] = useState(textFirst);
  const stage = useRef<HTMLDivElement>(null);
  const docMarks = marks.filter((m) => m.document_id === doc?.id);
  const asImage = isPdf && !textMode;

  useEffect(() => {
    const box = stage.current;
    const target = box?.querySelector(focus.claim ? `[data-claim="${focus.claim}"]` : "[data-hit]");
    if (!box) return;
    box.scrollTop = target ? box.scrollTop + target.getBoundingClientRect().top - box.getBoundingClientRect().top - 80 : 0;
  }, [focus, asImage, marks]);

  if (!doc) return <section className="panel col-doc empty">표시할 문서가 없습니다</section>;
  const label = documentLabel(doc.kind, doc.filename);

  return (
    <section className="panel col-doc" aria-label="원문">
      <div className="doc-toolbar">
        <div className="segmented" role="tablist" aria-label="문서 선택">
          {docs.map((d) => (
            <button key={d.id} type="button" role="tab" aria-selected={d.id === doc.id} onClick={() => onDoc(d.id)}>
              {documentLabel(d.kind, d.filename)}
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
        <span style={{ marginLeft: "auto" }}>{docMarks.length ? "원문은 수정하지 않고 그대로 보여줍니다" : emptyNote}</span>
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

/** Split a page's text at highlight edges; annotation offsets are relative to their page. */
export function segments(page: Page, marks: Annotation[]) {
  const local = marks
    .filter((m) => m.page === page.number)
    .map((m) => ({ m, from: Math.max(0, m.start), to: Math.min(page.text.length, m.end) }))
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
