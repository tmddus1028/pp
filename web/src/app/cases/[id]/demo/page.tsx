"use client";

import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
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

/** backend/cases.py create_advice / list_advice row. */
type AdviceRecord = {
  id: number;
  rejection_id: string;
  claim_number: number;
  provider: string;
  created_at: string;
  response: ImprovementResponse;
};

// 요약: 거절 이유 → 대응 전략 → 고른 전략으로 의견서 초안. 세부 입력은 '대응 방안' 탭에 그대로 있다.
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
    .replace(/(?:DEMO-)+\d+-[a-z_]+|KIPRIS-\d+-\d+-\d+-[a-z_]+/g, "비슷한 사례")
    .replace(
      /\b(clarify|narrow|add_limitation|remove_unsupported_scope|dependency_rewrite|argument_only)\b/g,
      (word) => `'${ACTION[word as Strategy["action_type"]]}'`,
    );
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
  const [advice, setAdvice] = useState<ImprovementResponse | null>(null);
  // "local" = no API key: a rule-based fallback, not an AI answer, so it must not be titled as one.
  const [adviceBy, setAdviceBy] = useState("");
  // Whether an AI provider is configured; without one, generation would only re-save the rule-based fallback.
  const [aiReady, setAiReady] = useState(false);
  useEffect(() => {
    api<{ ai: boolean }>("/cases/ai").then((s) => setAiReady(s.ai), () => setAiReady(false));
  }, []);
  const [chosen, setChosen] = useState<number | null>(null);
  // The card the attorney clicked; the bottom bar drafts from it.
  const [selected, setSelected] = useState<number | null>(null);
  const [draft, setDraft] = useState<OpinionResponse | null>(null);
  // The saved choice behind the draft; shown on its own when no saved AI answer exists for the issue.
  const [picked, setPicked] = useState<SelectionRecord | null>(null);
  const [busy, setBusy] = useState<"" | "advice" | "draft">("");
  const [error, setError] = useState("");
  // Results saved earlier for this issue. Kept aside and shown only when the attorney presses the
  // matching button, so nothing appears as if it had been generated without being asked for.
  const [saved, setSaved] = useState<{
    advice: AdviceRecord | null;
    draft: DraftRecord | null;
    selection: SelectionRecord | null;
  }>({ advice: null, draft: null, selection: null });

  useEffect(() => {
    if (!rejection) return;
    /* eslint-disable react-hooks/set-state-in-effect -- reset before the saved records arrive */
    setAdvice(null);
    setAdviceBy("");
    setDraft(null);
    setPicked(null);
    setChosen(null);
    setSelected(null);
    setSaved({ advice: null, draft: null, selection: null });
    /* eslint-enable react-hooks/set-state-in-effect */
    Promise.all([
      api<AdviceRecord[]>(`/cases/${meta.id}/advice`),
      api<SelectionRecord[]>(`/cases/${meta.id}/selections`),
      api<DraftRecord[]>(`/cases/${meta.id}/drafts`),
    ]).then(([advices, selections, drafts]) => {
      const mine = selections.filter((s) => s.rejection_id === rejection.rejection_id);
      const latest = drafts.find((d) => mine.some((s) => s.id === d.selection_id)) ?? null;
      setSaved({
        advice: advices.find((a) => a.rejection_id === rejection.rejection_id && a.claim_number === claim) ?? null,
        draft: latest,
        selection: (latest && mine.find((s) => s.id === latest.selection_id)) ?? null,
      });
    }, () => undefined);
  }, [claim, meta.id, rejection]);

  function ask() {
    if (!rejection) return;
    // First press shows what was saved for this issue (no AI call); later presses regenerate.
    if (!advice && saved.advice) {
      setAdvice(saved.advice.response);
      setAdviceBy(saved.advice.provider);
      return;
    }
    if (!aiReady) return;
    setBusy("advice");
    setError("");
    setChosen(null);
    setSelected(null);
    api<AdviceRecord>(
      `/cases/${meta.id}/advice`,
      json("POST", { claim_number: claim, rejection_id: rejection.rejection_id }),
    )
      .then(
        (made) => {
          setAdvice(made.response);
          setAdviceBy(made.provider);
        },
        (e: Error) => setError(e.message),
      )
      .finally(() => setBusy(""));
  }

  async function write(index: number) {
    if (!rejection || !advice) return;
    // Without AI the only draft there can be is the one saved for this issue.
    if (!aiReady) {
      if (saved.draft) {
        setChosen(index);
        setDraft(saved.draft.response);
        setPicked(saved.selection);
      }
      return;
    }
    setBusy("draft");
    setError("");
    setChosen(index);
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
  const highlighted =
    chosen ?? (picked ? strategies.findIndex((s) => picked.record.emphasize.startsWith(`${s.title}:`)) : -1);
  // Until the attorney clicks a card, the one behind the saved draft counts as selected;
  // -1 means they closed it again (clicking the open card toggles it shut).
  const current = selected === null ? (highlighted >= 0 ? highlighted : null) : selected >= 0 ? selected : null;
  const toggle = (i: number) => setSelected(current === i ? -1 : i);

  return (
    <div className="demo-grid">
      <section className="panel demo-col" aria-label="거절 이유">
        <StepHead n={1} title="거절 이유" />
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
      </section>

      <section className="panel demo-col" aria-label="대응 전략">
        <StepHead
          n={2}
          title={
            <>
              대응 전략{strategies.length ? ` ${strategies.length}건` : ""}
              {/* No API key: the fallback assembles strategies by rule, so say so instead of passing it off as AI. */}
              {adviceBy === "local" && <span className="tag">규칙 기반</span>}
            </>
          }
        />
        {!advice && busy !== "advice" && picked && (
          <>
            <article className="demo-card chosen">
              <div className="row" style={{ justifyContent: "space-between", gap: 8 }}>
                <span className="demo-num">이 초안을 만든 전략</span>
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
          </>
        )}
        {busy === "advice" && <p className="muted demo-empty">대응 전략을 만드는 중입니다…</p>}
        {advice && strategies.length === 0 && (
          <p className="muted demo-empty">원문 근거로 확인되는 대응 전략이 없습니다. &lsquo;대응 방안&rsquo; 탭에서 직접 정해 주세요.</p>
        )}
        {strategies.map((s, i) => (
          // Click a card to choose it; the bottom bar writes the draft from the chosen one.
          <article
            key={i}
            role="radio"
            aria-checked={current === i}
            tabIndex={0}
            className={`demo-card${current === i ? " chosen" : ""}`}
            onClick={() => toggle(i)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                toggle(i);
              }
            }}
          >
            <div className="row" style={{ justifyContent: "space-between", gap: 8 }}>
              <span className="demo-num">전략 {i + 1}</span>
              <span className="pill tone-info">{ACTION[s.action_type]}</span>
            </div>
            <h3 className="demo-title">{plain(s.title)}</h3>
            {/* Unchosen cards stay short so all three fit side by side for comparison; the chosen one opens. */}
            <p className={current === i ? "demo-text" : "demo-text clamp"}>{plain(s.description)}</p>
            {current === i && (
              <>
                <p className="demo-text">
                  <b>기대 효과</b> {plain(s.expected_effect)}
                </p>
                {s.tradeoff && (
                  <p className="hint" style={{ margin: 0 }}>
                    주의: {plain(s.tradeoff)}
                  </p>
                )}
              </>
            )}
            <span className="hint" style={{ margin: 0 }}>
              원문 근거 {s.grounding.length}곳{s.precedent_ids?.length ? ` · 비슷한 사례 ${s.precedent_ids.length}건` : ""}
            </span>
          </article>
        ))}
        {advice && <p className="hint">대응 전략은 검토용입니다. 최종 판단은 변리사가 합니다.</p>}
        {/* Stays at the bottom of this scrolling column, so it is reachable without scrolling past three cards. */}
        <div className="demo-cta-bar">
          <button
            type="button"
            className={advice ? "button" : "button primary"}
            disabled={!!busy || !(aiReady || (!advice && saved.advice))}
            title={
              aiReady || (!advice && saved.advice)
                ? undefined
                : "AI가 연결되지 않아 대응 전략을 생성할 수 없습니다 (.env의 ANTHROPIC_API_KEY)"
            }
            onClick={ask}
          >
            {busy === "advice" ? "원문을 읽는 중… (1~2분)" : advice ? "전략 다시 생성" : "대응 전략 생성"}
          </button>
          {strategies.length > 0 && (
            <button
              type="button"
              className="button primary"
              disabled={!!busy || current === null || !(aiReady || saved.draft)}
              onClick={() => current !== null && write(current)}
            >
              {busy === "draft" ? "초안 작성 중…" : "선택한 전략으로 초안 작성"}
            </button>
          )}
        </div>
      </section>

      <section className="panel demo-col" aria-label="의견서 초안">
        <StepHead
          n={3}
          title="의견서 초안"
          action={
            draft &&
            busy !== "draft" && (
              <button type="button" className="button sm" onClick={() => navigator.clipboard.writeText(draftText(draft))}>
                전체 복사
              </button>
            )
          }
        />
        {busy === "draft" && <Writing />}
        {!draft && busy !== "draft" && (
          <p className="muted demo-empty">가운데에서 전략 하나를 고르면 여기에 초안이 나옵니다.</p>
        )}
        {draft && busy !== "draft" && <Draft opinion={draft} />}
      </section>

      {error && <p className="error demo-error">{error}</p>}
    </div>
  );
}

/** Column heading; a column-wide action sits at its right so all three columns line up. */
function StepHead({ n, title, action }: { n: number; title: ReactNode; action?: ReactNode }) {
  return (
    <div className="demo-head-row">
      <h2 className="demo-head">
        <span className="demo-step">{String(n).padStart(2, "0")}</span>
        {title}
      </h2>
      {action}
    </div>
  );
}

// Waiting screen while the draft is written: heading and text lines fill in one after another, then repeat.
const WRITING_LINES: [kind: "head" | "text", width: number][] = [
  ["head", 30], ["text", 96], ["text", 88], ["text", 64],
  ["head", 36], ["text", 92], ["text", 97], ["text", 80], ["text", 52],
];

function Writing() {
  return (
    <div className="writing" role="status">
      <span className="sr-only">의견서 초안을 쓰는 중입니다</span>
      {WRITING_LINES.map(([kind, width], i) => (
        <span
          key={i}
          className={`writing-line ${kind}`}
          style={{ "--w": `${width}%`, animationDelay: `${i * 0.45}s` } as CSSProperties}
        />
      ))}
    </div>
  );
}

/** The whole draft as plain text, for 전체 복사. */
function draftText({ draft }: OpinionResponse) {
  return [
    draft.amended_claim ? `[보정 청구항]\n${draft.amended_claim}` : "",
    ...draft.sections.map((s) => `[${s.heading}]\n${s.paragraphs.map((p) => p.text).join("\n")}`),
  ]
    .filter(Boolean)
    .join("\n\n");
}

function Draft({ opinion }: { opinion: OpinionResponse }) {
  const { draft, changes } = opinion;
  return (
    <div className="stack" style={{ gap: 14 }}>
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
