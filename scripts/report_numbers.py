"""Recompute the numbers in the midterm deck (2026-10-20 final) from files in this repo.

uv run python scripts/report_numbers.py

No API key or KIPRIS quota needed. Explanations: docs/PRESENTATION_NUMBERS.md
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.precedents import repository as r  # noqa: E402

PRECEDENTS = ROOT / "data/precedents"


def jsonl(name):
    return [json.loads(line) for line in (PRECEDENTS / name).open(encoding="utf-8")]


def refusal_stats(applications=None):
    decisions = jsonl("kr_refusal_decisions.jsonl")
    if applications is not None:
        decisions = [d for d in decisions if d["application"] in applications]
    responded = [d for d in decisions if d["responded"]]
    with_table = sum(d["has_unresolved_table"] for d in responded)
    return len(decisions), len(responded), with_table


def pct(part, whole):
    return f"{part / whole:.0%}" if whole else "-"


def main():
    cases = {c["case_id"]: c for c in r.load(r.KR_PATH)}
    history = jsonl("kr_claim_history.jsonl")
    snapshot = json.loads((PRECEDENTS / "presentation_snapshot.json").read_text("utf-8"))

    print("[3p] 139개 출원 · 대응 사례 383건")
    print(f"    {len({c['application'] for c in cases.values()})}개 출원, {len(cases)}건")

    print("\n[3p] 청구항 변동 이력으로 보정 전후 청구항을 연결한 사례 314건")
    print(f"    {len(history)}건 / 전체 {len(cases)}건")

    linked = [(h, cases[h["case_id"]]) for h in history if h["case_id"] in cases]
    inventive = [(h, c) for h, c in linked if c["category"] == "inventive_step"]
    resolved = [h for h, c in inventive if c["outcome"] == "resolved"]
    granted = [h for h, c in inventive if c["next_action"] == "등록결정"]
    print("\n[3p] 75 / 83건 — 진보성 사례 중 실제 추가·변경 청구항 문구 확보")
    print(
        f"    해소된 진보성 사례 {len(resolved)}건 중"
        f" {sum(bool(h['added_limitation']) for h in resolved)}건"
    )
    print(
        f"    (등록결정만 세면 {len(granted)}건 중"
        f" {sum(bool(h['added_limitation']) for h in granted)}건)"
    )

    print("\n[3p] 80% — 대응한 거절결정 중 '해소되지 않은 부분' 표가 있는 비율")
    for label, subset in (
        (f"발표 숫자(초기 {len(snapshot['applications'])}개 출원)", set(snapshot["applications"])),
        (f"지금 데이터({len({c['application'] for c in cases.values()})}개 출원)", None),
    ):
        total, responded, with_table = refusal_stats(subset)
        print(
            f"    {label}: 거절결정 {total}건 → 대응 {responded}건 → 표 있음 {with_table}건"
            f" = {pct(with_table, responded)}"
        )

    print("\n[참고] 한국 진보성 사례의 보정 방식별 해소율 (발표에는 없음)")
    labeled = Counter(
        (h["response_method"], c["outcome"]) for h, c in inventive if c["outcome"] != "excluded"
    )
    for method in ("dependent_merge", "spec_limitation", "none"):
        done = labeled[(method, "resolved")]
        total = done + labeled[(method, "unresolved")]
        print(f"    {method}: {done} / {total} = {pct(done, total)}")

    print("\n[6p] 테스트 430개 통과 → uv run pytest -q 로 확인")
    print("[6p] 로컬 LLM 5건 중 1~2건 → docs/PRESENTATION_NUMBERS.md (실행 기록은 git 밖)")


if __name__ == "__main__":
    main()
