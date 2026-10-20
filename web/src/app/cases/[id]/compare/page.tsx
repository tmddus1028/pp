"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, json } from "@/lib/api";
import { describeStatute } from "@/lib/labels";
import type {
  Annotation,
  Direction,
  DraftRecord,
  OpinionResponse,
  PrecedentCase,
  PrecedentStats,
  ReviewEvidence,
  SelectionInput,
  SelectionRecord,
} from "@/lib/view-types";
import { useCase } from "../case-shell";
import { DocumentViewer, type Doc, type Focus } from "../document-viewer";

// 요구사항 5장: 사례 선제시 → 변리사의 쟁점별 선택·확정 기록 → 그 기록으로 초안 작성.
const DIRECTIONS: [Direction, string][] = [
  ["반박", "보정 없이 의견서로 반박"],
  ["보정", "청구항 보정"],
  ["반박과 보정", "보정하고 의견서로 반박"],
  ["추가 조사", "자료를 더 확인한 뒤 결정"],
  ["보류", "이번 초안에서 제외"],
];
const DRAFTABLE = new Set<Direction>(["반박", "보정", "반박과 보정"]);
const METHOD: Record<NonNullable<PrecedentCase["response_method"]>, string> = {
  spec_limitation: "명세서 구성 추가",
  dependent_merge: "종속항 병합",
  clarification: "기재 명확화",
  argument_only: "의견만",
  none: "청구항 변경 없음",
};
/** 1020190000844 → 10-2019-0000844 */
const appNo = (a: string) => (/^\d{13}$/.test(a) ? `${a.slice(0, 2)}-${a.slice(2, 6)}-${a.slice(6)}` : a);
const KIND_MARK: Record<string, Annotation["type"]> = {
  specification: "specification",
  claim: "direct_rejection",
  parent_claim: "direct_rejection",
};
const NAME_KEY = "pinpoint.attorney";

/** One evidence source → page-relative marks the shared viewer understands. */
function marksFor(source: ReviewEvidence, docs: Doc[]): Annotation[] {
  const { document_id, start, end, page_numbers } = source.evidence;
  const doc = docs.find((d) => d.id === document_id);
  if (!doc) return [];
  return page_numbers.flatMap((n) => {
    const page = doc.pages[n - 1];
    if (!page || Math.min(end, page.end) <= Math.max(start, page.start)) return [];
    return [
      {
        id: `${source.evidence_id}:${n}`,
        item_id: source.navigation_item,
        document_id,
        page: n,
        type: KIND_MARK[source.kind] ?? "citation",
        claim_number: null,
        statute: null,
        evidence_text: source.evidence.text,
        start: Math.max(start, page.start) - page.start,
        end: Math.min(end, page.end) - page.start,
        linked_rejection_id: null,
        linked_rejection_ids: [],
        boxes: [],
        bbox: null,
        location_method: "text",
      },
    ];
  });
}

/** Claim wording split at ';' / line breaks, so "keep" picks exact phrases the backend can check. */
function claimElements(text: string) {
  return text
    .split(/;|\n/)
    .map((s) => s.trim())
    .filter((s) => s.length > 4);
}

function readName() {
  try {
    return localStorage.getItem(NAME_KEY) ?? "";
  } catch {
    return "";
  }
}

export default function ResponsePage() {
  const { detail } = useCase();
  const { result, review, case: meta } = detail;
  const claims = review.items.filter((i) => i.kind === "claim" && (i.direct?.length || i.indirect?.length));
  const initial = Number(useSearchParams().get("claim")) || claims[0]?.claim_number || 1;
  const [claim, setClaim] = useState(initial);
  const rejections = result.rejections.filter((r) => r.claims.includes(claim) && r.action_type === "rejection");
  const [rejectionId, setRejectionId] = useState(rejections[0]?.rejection_id ?? "");
  const rejection = rejections.find((r) => r.rejection_id === rejectionId) ?? rejections[0];
  const claimText = result.patent.claims.find((c) => c.claim_number === claim)?.text ?? "";
  // Never offer this application's own later outcome as a precedent.
  const own =
    result.documents
      .map((d) => (d.source_metadata as { application_number?: string }).application_number)
      .find(Boolean) ?? "";

  const [stats, setStats] = useState<PrecedentStats | null>(null);
  const [similar, setSimilar] = useState<PrecedentCase[]>([]);
  const [selections, setSelections] = useState<SelectionRecord[]>([]);
  const [drafts, setDrafts] = useState<DraftRecord[]>([]);
  const [form, setForm] = useState<Omit<SelectionInput, "claim_number" | "rejection_id">>(() => ({
    precedent_ids: [],
    direction: "반박과 보정",
    emphasize: "",
    use_arguments: "",
    exclude_arguments: "",
    keep_elements: [],
    add_elements: "",
    forbidden_changes: "",
    confirmed_by: "",
  }));
  const [busy, setBusy] = useState<"" | "confirm" | "draft">("");
  const [error, setError] = useState("");
  const [focus, setFocus] = useState<Focus>({ doc: review.documents[0]?.id ?? "", nonce: 0 });
  const [marks, setMarks] = useState<Annotation[]>([]);

  const statute = rejection?.statute ?? "";
  useEffect(() => {
    if (!statute) return;
    const s = `statute=${encodeURIComponent(statute)}`;
    api<PrecedentStats>(`/precedents/stats?${s}`).then(setStats, () => setStats(null));
    const q = `&q=${encodeURIComponent(claimText.slice(0, 4000))}&exclude=${own}&limit=5`;
    api<PrecedentCase[]>(`/precedents/similar?${s}${q}`).then(setSimilar, () => setSimilar([]));
  }, [statute, claimText, own]);

  useEffect(() => {
    api<SelectionRecord[]>(`/cases/${meta.id}/selections`).then(setSelections, () => setSelections([]));
    api<DraftRecord[]>(`/cases/${meta.id}/drafts`).then(setDrafts, () => setDrafts([]));
  }, [meta.id]);

  // Name is a per-browser convenience; read once after mount (localStorage is client-only).
  useEffect(() => {
    const name = readName();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- browser storage exists only after mount (SSR-safe)
    if (name) setForm((f) => (f.confirmed_by ? f : { ...f, confirmed_by: name }));
  }, []);

  const history = selections.filter((s) => s.rejection_id === rejection?.rejection_id);
  const latest = history[0];
  const draft = latest && drafts.find((d) => history.some((h) => h.id === d.selection_id));
  const elements = claimElements(claimText);

  function show(sources: ReviewEvidence[], ids: string[]) {
    const found = ids.map((id) => sources.find((s) => s.evidence_id === id)).filter((s) => !!s);
    if (!found.length) return;
    setMarks(found.flatMap((s) => marksFor(s, review.documents)));
    setFocus((f) => ({ doc: found[0].evidence.document_id, nonce: f.nonce + 1 }));
  }

  function toggle<K extends "precedent_ids" | "keep_elements">(key: K, value: string) {
    setForm((f) => ({
      ...f,
      [key]: f[key].includes(value) ? f[key].filter((v) => v !== value) : [...f[key], value],
    }));
  }

  function confirm() {
    if (!rejection) return;
    setBusy("confirm");
    setError("");
    try {
      localStorage.setItem(NAME_KEY, form.confirmed_by);
    } catch {
      // per-browser convenience only
    }
    const body: SelectionInput = { ...form, claim_number: claim, rejection_id: rejection.rejection_id };
    api<SelectionRecord>(`/cases/${meta.id}/selections`, json("POST", body))
      .then((saved) => setSelections((list) => [saved, ...list]), (e: Error) => setError(e.message))
      .finally(() => setBusy(""));
  }

  function writeDraft() {
    if (!latest) return;
    setBusy("draft");
    setError("");
    api<DraftRecord>(`/cases/${meta.id}/drafts`, json("POST", { selection_id: latest.id }))
      .then((made) => setDrafts((list) => [made, ...list]), (e: Error) => setError(e.message))
      .finally(() => setBusy(""));
  }

  return (
    <div className="workspace">
      <section className="col-list" aria-label="대응 방향 선택">
        <div className="panel panel-pad stack" style={{ gap: 10 }}>
          <h2 className="section-title">대응할 쟁점</h2>
          <div className="row" style={{ gap: 8 }}>
            <label className="field">
              청구항
              <select value={claim} onChange={(e) => (setClaim(Number(e.target.value)), setRejectionId(""))}>
                {claims.map((c) => (
                  <option key={c.id} value={c.claim_number}>
                    청구항 {c.claim_number}
                  </option>
                ))}
              </select>
            </label>
            {rejections.length > 1 && (
              <label className="field">
                거절 이유
                <select value={rejection?.rejection_id} onChange={(e) => setRejectionId(e.target.value)}>
                  {rejections.map((r) => (
                    <option key={r.rejection_id} value={r.rejection_id}>
                      {describeStatute(r.statute).kind} · {r.statute}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
          {!rejection && <p className="muted" style={{ margin: 0 }}>이 청구항에 연결된 거절 이유가 없습니다.</p>}
        </div>

        {rejection && (
          <>
            <Step n={1} title="비슷한 과거 사례">
              {stats && (
                <p className="hint">
                  같은 유형({stats.label}) 실제 한국 사건 {stats.labeled}건 중 {stats.resolved}건 해소 · 유사도는 성공 가능성이 아닙니다
                </p>
              )}
              {similar.length ? (
                similar.map((c) => (
                  <label key={c.case_id} className="stack" style={{ gap: 4, cursor: "pointer" }}>
                    <span className="row" style={{ gap: 6 }}>
                      <input
                        type="checkbox"
                        checked={form.precedent_ids.includes(c.case_id)}
                        onChange={() => toggle("precedent_ids", c.case_id)}
                      />
                      <span style={{ fontSize: 13, fontWeight: 600 }}>참고 사례로 선택</span>
                    </span>
                    <CaseCard c={c} />
                  </label>
                ))
              ) : (
                <p className="muted" style={{ margin: 0 }}>비교할 수 있는 비슷한 사례가 없습니다.</p>
              )}
              {similar.some((c) => c.demo) && (
                <p className="hint">데모 사례는 같은 분야의 실제 사례가 없을 때 보여주는 가상 데이터입니다.</p>
              )}
            </Step>

            <Step n={2} title="대응 방향 선택과 확정">
              <fieldset className="stack" style={{ gap: 6, border: 0, padding: 0, margin: 0 }}>
                <legend className="label">대응 방향</legend>
                {DIRECTIONS.map(([value, hint]) => (
                  <label key={value} className="row" style={{ gap: 6, fontSize: 13 }}>
                    <input
                      type="radio"
                      name="direction"
                      checked={form.direction === value}
                      onChange={() => setForm({ ...form, direction: value })}
                    />
                    <b>{value}</b> <span className="muted">{hint}</span>
                  </label>
                ))}
              </fieldset>
              <Field label="강조할 차이점" value={form.emphasize} onChange={(v) => setForm({ ...form, emphasize: v })} />
              <Field label="사용할 주장" value={form.use_arguments} onChange={(v) => setForm({ ...form, use_arguments: v })} />
              <Field label="제외할 주장" value={form.exclude_arguments} onChange={(v) => setForm({ ...form, exclude_arguments: v })} />
              {form.direction !== "반박" && DRAFTABLE.has(form.direction) && (
                <>
                  <div>
                    <h3 className="label">유지할 구성 (현재 청구항 문구)</h3>
                    <div className="stack" style={{ gap: 4, maxHeight: 180, overflow: "auto" }}>
                      {elements.map((el) => (
                        <label key={el} className="row" style={{ gap: 6, fontSize: 12, alignItems: "flex-start" }}>
                          <input
                            type="checkbox"
                            checked={form.keep_elements.includes(el)}
                            onChange={() => toggle("keep_elements", el)}
                          />
                          <span>{el.length > 90 ? el.slice(0, 90) + "…" : el}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <Field
                    label="추가할 구성 (명세서에 있는 내용만)"
                    value={form.add_elements}
                    onChange={(v) => setForm({ ...form, add_elements: v })}
                  />
                  <Field
                    label="허용하지 않는 변경"
                    value={form.forbidden_changes}
                    onChange={(v) => setForm({ ...form, forbidden_changes: v })}
                  />
                </>
              )}
              <label className="stack" style={{ gap: 4 }}>
                <span className="label" style={{ margin: 0 }}>
                  확정하는 변리사
                </span>
                <input value={form.confirmed_by} maxLength={80} onChange={(e) => setForm({ ...form, confirmed_by: e.target.value })} />
              </label>
              <button
                type="button"
                className="button primary"
                disabled={!!busy || !form.confirmed_by.trim()}
                onClick={confirm}
              >
                {busy === "confirm" ? "저장 중…" : "선택 확정"}
              </button>
              {history.length > 0 && (
                <ul className="hint" style={{ paddingLeft: 18, margin: 0 }}>
                  {history.map((h) => (
                    <li key={h.id}>
                      v{h.version} · {h.record.direction} · 참고 사례 {h.record.precedent_ids.length}건 · {h.confirmed_by} ·{" "}
                      {new Date(h.confirmed_at).toLocaleString("ko-KR")}
                    </li>
                  ))}
                </ul>
              )}
            </Step>

            <Step n={3} title="초안 작성">
              {latest ? (
                <>
                  <p className="hint" style={{ margin: 0 }}>
                    확정된 v{latest.version}({latest.record.direction}) 기록으로 작성합니다
                  </p>
                  <button
                    type="button"
                    className="button"
                    disabled={!!busy || !DRAFTABLE.has(latest.record.direction)}
                    onClick={writeDraft}
                  >
                    {busy === "draft"
                      ? "초안 작성 중… (로컬 AI, 수 분 걸릴 수 있음)"
                      : DRAFTABLE.has(latest.record.direction)
                        ? "의견서 초안 작성"
                        : `'${latest.record.direction}'은 초안을 작성하지 않습니다`}
                  </button>
                </>
              ) : (
                <p className="muted" style={{ margin: 0 }}>먼저 대응 방향을 확정하세요.</p>
              )}
            </Step>
          </>
        )}
        {error && <p className="error">{error}</p>}
      </section>

      <DocumentViewer
        caseId={meta.id}
        docs={review.documents}
        focus={focus}
        marks={marks}
        onDoc={(doc) => setFocus((f) => ({ doc, nonce: f.nonce + 1 }))}
        emptyNote="근거 칩을 누르면 원문 위치를 표시합니다"
        textFirst
      />

      <aside className="panel col-detail" aria-label="의견서 초안">
        {draft ? (
          <>
            <p className="hint" style={{ margin: 0 }}>
              선택 기록 v{history.find((h) => h.id === draft.selection_id)?.version} · {draft.provider} {draft.model} ·{" "}
              {new Date(draft.created_at).toLocaleString("ko-KR")}
            </p>
            <Opinion opinion={draft.response} onShow={(ids) => show(draft.response.sources, ids)} />
          </>
        ) : (
          <p className="muted" style={{ margin: 0 }}>
            사례를 보고 대응 방향을 확정하면, 그 기록으로 보정 청구항과 의견서 초안을 작성합니다. 모든 문단은 원문 인용과 대조한 뒤에만 표시합니다.
          </p>
        )}
      </aside>
    </div>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <div className="panel panel-pad stack" style={{ gap: 10 }}>
      <h2 className="section-title">
        {n}. {title}
      </h2>
      {children}
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="stack" style={{ gap: 4 }}>
      <span className="label" style={{ margin: 0 }}>
        {label}
      </span>
      <textarea rows={2} maxLength={2000} value={value} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

function CaseCard({ c }: { c: PrecedentCase }) {
  return (
    <div className="ref-card">
      <div className="top">
        <span className="name" style={{ fontSize: 13 }}>
          {c.title ?? appNo(c.application)}
          {c.demo && (
            <span className="pill tone-plain" style={{ marginLeft: 6 }}>
              데모
            </span>
          )}
        </span>
        <span className={`pill ${c.outcome === "resolved" ? "tone-done" : "tone-direct"}`}>
          {c.outcome === "resolved" ? "등록" : "거절"} ·{" "}
          {c.response_method ? METHOD[c.response_method] : c.response_type === "amendment" ? "보정" : "의견만"}
        </span>
      </div>
      {c.added_limitation && (
        <span style={{ fontSize: 12, lineHeight: 1.6 }}>
          <b>추가·변경한 문구</b>{" "}
          {c.added_limitation.length > 240 ? c.added_limitation.slice(0, 240) + "…" : c.added_limitation}
        </span>
      )}
      {c.amendment_documents?.length ? (
        <span className="hint" style={{ margin: 0 }}>
          {c.amendment_documents.join(" · ")}
        </span>
      ) : null}
      {c.outcome !== "resolved" && c.argument_excerpt && (
        <span className="hint" style={{ margin: 0 }}>
          {c.argument_excerpt.slice(0, 160)}
        </span>
      )}
    </div>
  );
}

function Evidence({
  grounding,
  onShow,
}: {
  grounding: { evidence_id: string; quote: string }[];
  onShow: (ids: string[]) => void;
}) {
  if (!grounding.length) return null;
  return (
    <span className="chips">
      {grounding.map((g, i) => (
        <button
          key={i}
          type="button"
          className="chip tone-cite"
          style={{ border: 0, cursor: "pointer", whiteSpace: "normal", textAlign: "left" }}
          title={g.quote}
          onClick={() => onShow([g.evidence_id])}
        >
          {g.evidence_id} · {g.quote.length > 28 ? g.quote.slice(0, 28) + "…" : g.quote}
        </button>
      ))}
    </span>
  );
}

function Opinion({ opinion, onShow }: { opinion: OpinionResponse; onShow: (ids: string[]) => void }) {
  const { draft, changes } = opinion;
  const text = [
    draft.amended_claim ? `[보정 청구항]\n${draft.amended_claim}` : "",
    ...draft.sections.map((s) => `[${s.heading}]\n${s.paragraphs.map((p) => p.text).join("\n")}`),
  ]
    .filter(Boolean)
    .join("\n\n");
  return (
    <>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2 style={{ fontSize: 18 }}>의견서 초안</h2>
        <button type="button" className="button" onClick={() => navigator.clipboard.writeText(text)}>
          복사
        </button>
      </div>
      {draft.amended_claim && (
        <div>
          <h3 className="label">보정 청구항 (추가 부분 강조)</h3>
          <p style={{ margin: 0, fontSize: 13, lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
            {changes.map((c, i) =>
              c.change_type === "removed" ? null : c.change_type === "unchanged" ? (
                c.revised
              ) : (
                <ins key={i} className="mark-specification" style={{ textDecoration: "none" }}>
                  {c.revised}
                </ins>
              ),
            )}
          </p>
        </div>
      )}
      {draft.sections.map((s) => (
        <div key={s.heading}>
          <h3 className="label">{s.heading}</h3>
          {s.paragraphs.map((p, i) => (
            <div key={i} className="stack" style={{ gap: 6, marginBottom: 10 }}>
              <p style={{ margin: 0, fontSize: 13, lineHeight: 1.7 }}>{p.text}</p>
              <Evidence grounding={p.grounding} onShow={onShow} />
            </div>
          ))}
        </div>
      ))}
      <ul className="hint" style={{ paddingLeft: 18 }}>
        {draft.cautions.map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ul>
    </>
  );
}
