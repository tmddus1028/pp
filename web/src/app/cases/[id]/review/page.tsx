"use client";

import { useCase } from "../case-shell";

// Phase 3: port frontend/pdf_review_component (viewer + highlights + review panel).
export default function ReviewPage() {
  const { detail } = useCase();
  const pdfs = detail.review.documents.filter((d) => d.filename.toLowerCase().endsWith(".pdf"));
  const id = detail.case.id;
  return (
    <section className="stack">
      <p className="muted">PDF 검토 화면은 다음 단계에서 이식합니다. 저장된 원문 확인:</p>
      <ul>
        {pdfs.map((d) => (
          <li key={d.id}>
            <a href={`/api/cases/${id}/files/${d.id}`} target="_blank" rel="noreferrer">
              {d.filename}
            </a>{" "}
            <span className="muted">· {d.pages.length}쪽</span>
          </li>
        ))}
      </ul>
      <p className="muted">
        하이라이트 {detail.review.annotations.length}개 · 좌표 확인{" "}
        {detail.review.annotations.filter((a) => a.boxes.length).length}개
      </p>
    </section>
  );
}
