"use client";

import { useEffect, useState } from "react";
import { api, json } from "@/lib/api";
import { describeStatute } from "@/lib/labels";
import type {
  DraftRecord,
  ImprovementResponse,
  OpinionResponse,
  SelectionInput,
  SelectionRecord,
  Strategy,
} from "@/lib/view-types";
import { useCase } from "../case-shell";

// 간단 보기: 거절 이유 → AI 추천 3개 → 고른 추천으로 의견서 초안. 세부 입력은 '대응 방안' 탭에 그대로 있다.
const ACTION: Record<Strategy["action_type"], string> = {
  clarify: "문구 명확화",
  narrow: "범위 좁히기",
  add_limitation: "구성 추가",
  remove_unsupported_scope: "근거 없는 범위 삭제",
  dependency_rewrite: "종속항 병합",
  argument_only: "보정 없이 주장",
  other: "기타",
};
const NAME_KEY = "pinpoint.attorney";
const BRIEF = 260;

/** First sentences of the examiner's reasoning, cut at a sentence end when one is close. */
function brief(text: string) {
  if (text.length <= BRIEF) return text;
  const cut = text.slice(0, BRIEF);
  const end = Math.max(cut.lastIndexOf("다."), cut.lastIndexOf(". "));
  return (end > 120 ? cut.slice(0, end + 2) : cut) + " …";
}

/** Model text for the screen: drop internal enum names and precedent ids. */
function plain(text: string) {
  return text
    .replace(/\s*\((?:clarify|narrow|add_limitation|remove_unsupported_scope|dependency_rewrite|argument_only|other)\)/g, "")
    .replace(/(?:DEMO-)+\d+-[a-z_]+|KIPRIS-\d+-\d+-\d+-[a-z_]+/g, "비슷한 사례");
}

function stored<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function remember(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // per-browser convenience only: a failed write just means asking the AI again
  }
}

function reviewer() {
  try {
    return localStorage.getItem(NAME_KEY) || "검토자";
  } catch {
    return "검토자";
  }
}

/** One AI strategy → the same selection record the detailed form saves. */
function toSelection(s: Strategy, claim: number, rejectionId: string): SelectionInput {
  const argue = s.action_type === "argument_only";
  return {
    claim_number: claim,
    rejection_id: rejectionId,
    precedent_ids: (s.precedent_ids ?? []).slice(0, 10),
    direction: argue ? "반박" : "반박과 보정",
    emphasize: `${s.title}: ${s.description}`.slice(0, 2000),
    use_arguments: s.expected_effect.slice(0, 2000),
    exclude_arguments: "",
    keep_elements: [],
    add_elements: argue ? "" : s.description.slice(0, 2000),
    forbidden_changes: "",
    confirmed_by: reviewer(),
  };
}

export default function DemoPage() {
  const { detail } = useCase();
  const { result, case: meta } = detail;
  const rejections = result.rejections.filter((r) => r.action_type === "rejection");
  const [rejectionId, setRejectionId] = useState(rejections[0]?.rejection_id ?? "");
  const rejection = rejections.find((r) => r.rejection_id === rejectionId) ?? rejections[0];
  const claim = rejection?.primary_claims?.[0] ?? rejection?.claims[0] ?? 1;
  const claimText = result.patent.claims.find((c) => c.claim_number === claim)?.text ?? "";
  const key = `pinpoint.demo.${meta.id}.${rejection?.rejection_id}.${claim}`;

  const [advice, setAdvice] = useState<ImprovementResponse | null>(null);
  const [chosen, setChosen] = useState<number | null>(null);
  const [draft, setDraft] = useState<OpinionResponse | null>(null);
  // The saved choice behind the draft: AI answers live only in this browser, choices live on the server.
  const [picked, setPicked] = useState<SelectionRecord | null>(null);
  const [busy, setBusy] = useState<"" | "advice" | "draft">("");
  const [error, setError] = useState("");

  // Restore this tab's earlier AI answer and the newest saved draft for the issue (no new API call).
  useEffect(() => {
    if (!rejection) return;
    /* eslint-disable react-hooks/set-state-in-effect -- browser storage exists only after mount */
    setAdvice(stored<ImprovementResponse>(key));
    setChosen(stored<number>(key + ".chosen"));
    setDraft(null);
    setPicked(null);
    /* eslint-enable react-hooks/set-state-in-effect */
    Promise.all([
      api<SelectionRecord[]>(`/cases/${meta.id}/selections`),
      api<DraftRecord[]>(`/cases/${meta.id}/drafts`),
    ]).then(([selections, drafts]) => {
      const mine = selections.filter((s) => s.rejection_id === rejection.rejection_id);
      const latest = drafts.find((d) => mine.some((s) => s.id === d.selection_id));
      if (!latest) return;
      setDraft(latest.response);
      setPicked(mine.find((s) => s.id === latest.selection_id) ?? null);
    }, () => undefined);
  }, [key, meta.id, rejection]);

  function ask() {
    if (!rejection) return;
    setBusy("advice");
    setError("");
    setChosen(null);
    api<ImprovementResponse>(
      "/improvements",
      json("POST", { analysis: result, claim_number: claim, rejection_id: rejection.rejection_id }),
    )
      .then((made) => (setAdvice(made), remember(key, made)), (e: Error) => setError(e.message))
      .finally(() => setBusy(""));
  }

  async function write(index: number) {
    if (!rejection || !advice) return;
    setBusy("draft");
    setError("");
    setChosen(index);
    remember(key + ".chosen", index);
    try {
      const body = toSelection(advice.suggestion.strategies[index], claim, rejection.rejection_id);
      const saved = await api<SelectionRecord>(`/cases/${meta.id}/selections`, json("POST", body));
      const made = await api<DraftRecord>(`/cases/${meta.id}/drafts`, json("POST", { selection_id: saved.id }));
      setDraft(made.response);
      setPicked(saved);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }

  if (!rejection) {
    return <p className="muted">이 사건에는 대응할 거절 이유가 없습니다.</p>;
  }
  const kind = describeStatute(rejection.statute).kind;
  const strategies = advice?.suggestion.strategies.slice(0, 3) ?? [];

  return (
    <div className="demo-grid">
      <section className="panel demo-col" aria-label="거절 이유">
        <StepHead n={1} title="왜 거절됐나" />
        {rejections.length > 1 && (
          <select value={rejection.rejection_id} onChange={(e) => setRejectionId(e.target.value)}>
            {rejections.map((r) => (
              <option key={r.rejection_id} value={r.rejection_id}>
                {describeStatute(r.statute).kind} · 청구항 {r.claims.join(", ")}
              </option>
            ))}
          </select>
        )}
        <div className="row" style={{ gap: 8 }}>
          <span className="pill tone-direct">{kind}</span>
          <span className="hint" style={{ margin: 0 }}>
            {rejection.statute} · 청구항 {rejection.claims.join(", ")}
          </span>
        </div>
        <p className="demo-quote">{brief(rejection.reason_summary || rejection.examiner_explanation)}</p>
        {(rejection.reason_summary || rejection.examiner_explanation).length > BRIEF && (
          <details>
            <summary className="label" style={{ cursor: "pointer" }}>
              심사관 지적 전문 보기
            </summary>
            <p className="hint" style={{ whiteSpace: "pre-wrap", lineHeight: 1.7 }}>
              {rejection.examiner_explanation || rejection.reason_summary}
            </p>
          </details>
        )}
        {rejection.cited_references.length > 0 && (
          <div>
            <h3 className="label">심사관이 든 선행문헌</h3>
            <div className="chips">
              {rejection.cited_references.map((c) => (
                <span key={c.citation_id} className="chip tone-cite">
                  {c.name ?? c.citation_id}
                  {c.publication_number ? ` · ${c.publication_number}` : ""}
                </span>
              ))}
            </div>
          </div>
        )}
        <details>
          <summary className="label" style={{ cursor: "pointer" }}>
            청구항 {claim} 원문 보기
          </summary>
          <p className="hint" style={{ whiteSpace: "pre-wrap", lineHeight: 1.7 }}>
            {claimText}
          </p>
        </details>
        <button type="button" className="button primary demo-cta" disabled={!!busy} onClick={ask}>
          {busy === "advice" ? "AI가 원문을 읽는 중… (1~2분)" : advice ? "AI 추천 다시 받기" : "AI 추천 받기 →"}
        </button>
      </section>

      <section className="panel demo-col" aria-label="AI 추천">
        <StepHead n={2} title="AI 추천 3가지" />
        {!advice && busy !== "advice" && picked && (
          <>
            <article className="demo-card chosen">
              <div className="row" style={{ justifyContent: "space-between", gap: 8 }}>
                <span className="demo-num">이 초안을 만든 추천</span>
                <span className="pill tone-info">{picked.record.direction}</span>
              </div>
              <p className="demo-text">{plain(picked.record.emphasize)}</p>
              {picked.record.use_arguments && (
                <p className="demo-text">
                  <b>기대 효과</b> {plain(picked.record.use_arguments)}
                </p>
              )}
              <span className="hint" style={{ margin: 0 }}>
                {picked.confirmed_by} · {new Date(picked.confirmed_at).toLocaleString("ko-KR")}
              </span>
            </article>
            <p className="hint">다른 추천을 보려면 왼쪽의 &lsquo;AI 추천 받기&rsquo;를 누르세요.</p>
          </>
        )}
        {!advice && busy !== "advice" && !picked && (
          <p className="muted demo-empty">왼쪽의 &lsquo;AI 추천 받기&rsquo;를 누르면 통지서·명세서 원문을 근거로 대응 방법을 제안합니다.</p>
        )}
        {busy === "advice" && <p className="muted demo-empty">추천을 만드는 중입니다…</p>}
        {advice && strategies.length === 0 && (
          <p className="muted demo-empty">원문 근거로 확인되는 추천이 없습니다. &lsquo;대응 방안&rsquo; 탭에서 직접 정해 주세요.</p>
        )}
        {strategies.map((s, i) => (
          <article key={i} className={`demo-card${chosen === i ? " chosen" : ""}`}>
            <div className="row" style={{ justifyContent: "space-between", gap: 8 }}>
              <span className="demo-num">추천 {i + 1}</span>
              <span className="pill tone-info">{ACTION[s.action_type]}</span>
            </div>
            <h3 className="demo-title">{plain(s.title)}</h3>
            <p className="demo-text">{plain(s.description)}</p>
            <p className="demo-text">
              <b>기대 효과</b> {plain(s.expected_effect)}
            </p>
            {s.tradeoff && (
              <p className="hint" style={{ margin: 0 }}>
                주의: {plain(s.tradeoff)}
              </p>
            )}
            <div className="row" style={{ justifyContent: "space-between", gap: 8 }}>
              <span className="hint" style={{ margin: 0 }}>
                원문 근거 {s.grounding.length}곳{s.precedent_ids?.length ? ` · 비슷한 사례 ${s.precedent_ids.length}건` : ""}
              </span>
              <button type="button" className="button primary" disabled={!!busy} onClick={() => write(i)}>
                {busy === "draft" && chosen === i ? "초안 쓰는 중…" : "이걸로 초안 쓰기"}
              </button>
            </div>
          </article>
        ))}
        {advice && <p className="hint">AI 추천은 검토용입니다. 최종 판단은 변리사가 합니다.</p>}
      </section>

      <section className="panel demo-col" aria-label="의견서 초안">
        <StepHead n={3} title="의견서 초안" />
        {busy === "draft" && <p className="muted demo-empty">고른 추천으로 보정 청구항과 의견서를 쓰는 중입니다… (1~3분)</p>}
        {!draft && busy !== "draft" && (
          <p className="muted demo-empty">가운데에서 추천 하나를 고르면 여기에 초안이 나옵니다.</p>
        )}
        {draft && busy !== "draft" && <Draft opinion={draft} />}
      </section>

      {error && <p className="error demo-error">{error}</p>}
    </div>
  );
}

function StepHead({ n, title }: { n: number; title: string }) {
  return (
    <h2 className="demo-head">
      <span className="demo-step">{n}</span>
      {title}
    </h2>
  );
}

function Draft({ opinion }: { opinion: OpinionResponse }) {
  const { draft, changes } = opinion;
  const text = [
    draft.amended_claim ? `[보정 청구항]\n${draft.amended_claim}` : "",
    ...draft.sections.map((s) => `[${s.heading}]\n${s.paragraphs.map((p) => p.text).join("\n")}`),
  ]
    .filter(Boolean)
    .join("\n\n");
  return (
    <div className="stack" style={{ gap: 14 }}>
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button type="button" className="button" onClick={() => navigator.clipboard.writeText(text)}>
          전체 복사
        </button>
      </div>
      {draft.amended_claim && (
        <div>
          <h3 className="label">보정 청구항 (추가된 부분 강조)</h3>
          <p className="demo-text" style={{ whiteSpace: "pre-wrap" }}>
            {changes.map((c, i) =>
              c.change_type === "removed" ? null : c.change_type === "unchanged" ? (
                plain(c.revised)
              ) : (
                <ins key={i} className="mark-specification" style={{ textDecoration: "none" }}>
                  {plain(c.revised)}
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
            <p key={i} className="demo-text" style={{ marginBottom: 8 }}>
              {plain(p.text)}
            </p>
          ))}
        </div>
      ))}
      {draft.cautions.length > 0 && (
        <ul className="hint" style={{ paddingLeft: 18 }}>
          {draft.cautions.map((c) => (
            <li key={c}>{plain(c)}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
