"use client";

import { useCase } from "../case-shell";

// Phase 3: port frontend/evidence_comparison.py over GET /cases/{id}/comparison.
export default function ComparePage() {
  const { detail, t } = useCase();
  return (
    <p className="muted">
      근거 비교는 다음 단계에서 이식합니다. {t("거절 사유")} {detail.result.rejections.length}개
    </p>
  );
}
