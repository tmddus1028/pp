/** Plain-Korean labels for generated values. Source evidence text is never rewritten. */

const US_KIND: Record<string, string> = {
  "101": "특허 적격성 없음",
  "102": "신규성 없음",
  "103": "진보성 없음",
  "112": "기재 요건 위반",
  "112(a)": "명세서 기재 요건 위반",
  "112(b)": "기재 불명확",
  "112(d)": "종속항 형식 위반",
};

const KR_KIND: Record<string, string> = {
  "29-1": "신규성 없음",
  "29-2": "진보성 없음",
  "29-3": "확대된 선출원 위반",
  "29-4": "확대된 선출원 위반",
  "32": "특허받을 수 없는 발명",
  "36": "선출원 위반",
  "42": "기재 요건 위반",
  "42-3": "발명의 설명 기재 요건 위반",
  "42-4": "청구범위 기재 요건 위반",
  "45": "하나의 출원 범위 위반",
  "47-2": "보정 범위 초과",
};

/** "35 USC 112(b)" → 기재 불명확 · 미국 특허법 제112조 b항; "특허법 제29조제2항" → 진보성 없음. */
export function describeStatute(statute: string, objection = false) {
  const us = statute.match(/35\s*U\.?\s*S\.?\s*C\.?\s*§*\s*(\d+)((?:\s*\([a-z0-9]+\))*)/i);
  if (us) {
    const [section, ...parts] = [us[1], ...[...us[2].matchAll(/\(([a-z0-9]+)\)/gi)].map((m) => m[1])];
    const law = `미국 특허법 제${section}조` + (parts[0] ? ` ${parts[0]}항` : "") + (parts[1] ? ` ${parts[1]}호` : "");
    return { kind: objection ? "형식 지적" : US_KIND[`${section}(${parts[0]})`] ?? US_KIND[section] ?? "거절 이유", law };
  }
  const kr = statute.match(/제\s*(\d+)\s*조(?:\s*제\s*(\d+)\s*항)?/);
  if (kr) {
    const kind = KR_KIND[`${kr[1]}-${kr[2]}`] ?? KR_KIND[kr[1]] ?? "거절 이유";
    return { kind: objection ? "형식 지적" : kind, law: statute };
  }
  return { kind: objection ? "형식 지적" : "거절 이유", law: statute === "unknown" ? "법조항 확인 필요" : statute };
}

/** Days until a YYYY-MM-DD deadline, counted in local calendar days. */
export function deadlineLabel(deadline: string | null, today = new Date()) {
  if (!deadline) return { text: "기한 없음", soon: false };
  const start = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  const days = Math.round((Date.parse(deadline) - start) / 86_400_000);
  if (days === 0) return { text: "오늘 마감", soon: true };
  return days > 0 ? { text: `${days}일 남음`, soon: days <= 14 } : { text: `${-days}일 지남`, soon: true };
}

export const CITATION_ROLE: Record<string, string> = {
  relied_upon: "거절 근거 문헌",
  supporting_evidence: "보조 근거 문헌",
  not_relied_upon: "참고 문헌",
};

export const CLAIM_ROLES = [
  ["direct", "거절된 청구항", "tone-direct"],
  ["dep", "함께 검토할 종속항", "tone-dep"],
  ["objected", "형식 지적 청구항", "tone-info"],
  ["canceled", "삭제된 청구항", "canceled"],
  ["other", "지적 없는 청구항", "other"],
] as const;

export function claimRole(claim: { status?: string; direct?: string[]; indirect?: string[]; objected?: string[] }) {
  if (claim.status === "canceled") return CLAIM_ROLES[3];
  if (claim.direct?.length) return CLAIM_ROLES[0];
  if (claim.indirect?.length) return CLAIM_ROLES[1];
  if (claim.objected?.length) return CLAIM_ROLES[2];
  return CLAIM_ROLES[4];
}

export function documentLabel(kind: string, korean: boolean, filename: string) {
  if (kind === "office_action") return korean ? "의견제출통지서" : "심사관 통지서";
  if (kind === "patent") return korean ? "명세서와 청구범위" : "출원 청구항";
  return "선행문헌 원문 · " + filename.replace(/\.[^.]+$/, "");
}
