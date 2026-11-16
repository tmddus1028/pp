import Link from "next/link";
import { TrySample } from "./try-sample";

// Numbers come from docs/PRESENTATION_NUMBERS.md (scripts/report_numbers.py); update both together.
const STATS = [
  { value: "333만", unit: "건", label: "의견제출통지서 전체 통계", note: "KIPRISPlus 1999~2022" },
  { value: "1,638", unit: "건", label: "실제 대응 사례", note: "687개 출원 · KIPRIS" },
  { value: "594", unit: "건", label: "보정 전후 청구항 연결", note: "청구항 변동 이력" },
  { value: "64", unit: "%", label: "대응 전략 3개 안에 실제 등록 보정", note: "등록 90건 채점 · 비슷한 방향 포함" },
];

const STEPS = [
  { title: "두 문서를 올립니다", text: "특허 공보(명세서·청구범위) PDF와 의견제출통지서 XML 또는 PDF. 원본은 바꾸지 않습니다." },
  { title: "거절 근거를 짚어냅니다", text: "거절 이유, 인용발명, 심사관이 짚은 단락, 영향받는 종속항까지 원문 위치와 함께 정리합니다." },
  { title: "사례로 대응을 정합니다", text: "같은 거절이 실제로 해소된 사례를 보고 변리사가 방향을 고르면, 그 선택으로 의견서 초안을 씁니다." },
];

const FEATURES = [
  { title: "원문 근거 하이라이트", text: "통지서의 지적이 명세서·인용발명의 어느 문장인지 PDF 위에 바로 표시합니다." },
  { title: "해소 사례 검색", text: "비슷한 기술·같은 거절 이유에서 보정이나 의견으로 해소된 실제 사건을 찾아 보여줍니다." },
  { title: "근거 검증 의견서 초안", text: "원문에 없는 인용, 근거 없는 주장, 신규사항 추가를 걸러낸 초안만 내놓습니다." },
];

const PRINCIPLES = [
  "판단은 변리사가, AI는 근거를 찾고 정리합니다.",
  "모든 제안에 원문 위치와 비슷한 실제 사례를 붙입니다.",
  "근거가 맞지 않으면 제안하지 않고 비워 둡니다.",
  "공개 데이터(KIPRIS·KIPRISPlus)만 씁니다.",
];

export default function Landing() {
  return (
    <div className="lp">
      <section className="lp-hero lp-wrap">
        <div className="lp-hero-text">
          <p className="lp-eyebrow">특허 거절 대응 검토</p>
          <h1>
            거절 근거를
            <br />
            글 속에서 <em>정확히.</em>
          </h1>
          <p className="lp-lead">
            의견제출통지서와 명세서를 올리면 거절 이유·인용발명·청구항 관계를 원문 위치와 함께 정리하고, 실제로 해소된
            사례를 근거로 대응 방향과 의견서 초안을 제안합니다.
          </p>
          <div className="row">
            <Link href="/cases" className="button primary lp-cta">
              사건 등록하기
            </Link>
            <TrySample />
          </div>
        </div>
        <HeroMock />
      </section>

      <section className="lp-stats" aria-label="데이터 규모">
        <dl className="lp-wrap lp-stat-grid">
          {STATS.map((s) => (
            <div key={s.label}>
              <dt>{s.label}</dt>
              <dd>
                {s.value}
                <span>{s.unit}</span>
              </dd>
              <p>{s.note}</p>
            </div>
          ))}
        </dl>
      </section>

      <section className="lp-section lp-wrap">
        <p className="lp-eyebrow">진행 방식</p>
        <h2>세 단계로 끝나는 거절 검토</h2>
        <ol className="lp-steps">
          {STEPS.map((s, i) => (
            <li key={s.title} className="panel">
              <span className="lp-step-num">{String(i + 1).padStart(2, "0")}</span>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="lp-section lp-alt">
        <div className="lp-wrap">
          <p className="lp-eyebrow">주요 기능</p>
          <h2>검토에 필요한 근거를 한 화면에</h2>
          <div className="lp-features">
            {FEATURES.map((f) => (
              <div key={f.title} className="lp-feature">
                <h3>{f.title}</h3>
                <p>{f.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="lp-section lp-wrap lp-principles">
        <div>
          <h2>변리사를 대신하지 않습니다.</h2>
          <p className="lp-lead">검토와 초안 작성 시간은 줄이고. 판단하는 시간은 늘리고.</p>
        </div>
        <ul>
          {PRINCIPLES.map((p) => (
            <li key={p}>
              <svg viewBox="0 0 24 24" width={20} height={20} aria-hidden="true">
                <circle cx="12" cy="12" r="9" fill="none" stroke="var(--accent)" strokeWidth="2.4" />
                <circle cx="12" cy="12" r="3.4" fill="var(--accent)" />
              </svg>
              {p}
            </li>
          ))}
        </ul>
      </section>

      <section className="lp-final">
        <div className="lp-wrap">
          <h2>다음 의견제출통지서, PINPOINT로 검토해 보세요.</h2>
          <Link href="/cases" className="button lp-cta lp-cta-invert">
            사건 등록하기
          </Link>
        </div>
      </section>

      <footer className="lp-footer lp-wrap">
        <span>PINPOINT · 특허 거절 대응 검토</span>
        <span>결과는 검토 보조용이며 법률 자문이 아닙니다.</span>
      </footer>
    </div>
  );
}

// A static picture of the review screen: a notice excerpt with the found passage pinned.
function HeroMock() {
  return (
    <div className="lp-mock" aria-hidden="true">
      <div className="lp-mock-bar">
        <i />
        <i />
        <i />
        <span>PINPOINT · 거절 이유 검토</span>
      </div>
      <div className="lp-mock-body">
        <div className="row" style={{ gap: 8 }}>
          <span className="pill tone-direct">진보성 없음</span>
          <span className="muted" style={{ fontSize: 13 }}>
            특허법 제29조제2항 · 청구항 1
          </span>
        </div>
        <p className="lp-mock-text">
          청구항 1의 쿠폰 발행부는 인용발명 2의 쿠폰 발급 요청에 따른 처리 구성과 대비하여,{" "}
          <mark className="mark-direct">단말 정보에 따라 발행 형식을 결정하는 구성</mark>이 통상의 기술자에게 쉽게
          도출될 수 있는 것으로 판단됩니다.
        </p>
        <div className="lp-mock-refs">
          <span className="chip tone-cite">인용발명 2 · [0041]</span>
          <span className="chip tone-cite">인용발명 3 · [0055]</span>
          <span className="chip tone-dep">종속항 3, 5 영향</span>
        </div>
        <div className="lp-mock-card">
          <span className="demo-num">비슷한 해소 사례</span>
          <b>종속항 구성을 독립항에 병합해 등록</b>
          <span className="muted">같은 거절 이유 · 전자상거래 분야</span>
        </div>
      </div>
    </div>
  );
}
