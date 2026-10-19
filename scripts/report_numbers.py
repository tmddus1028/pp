"""Recompute every number in the midterm deck from files in this repo.

uv run python scripts/report_numbers.py

No API key or KIPRIS quota needed. Explanations: docs/PRESENTATION_NUMBERS.md
"""

import json
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.precedents import repository as r  # noqa: E402

PRECEDENTS = ROOT / "data/precedents"
CASE_0844 = ROOT / "korean_prototype/data/kr_1020190000844"
PATENT = "KR20190025857A.pdf"
CITATIONS = ["KR20150096573A.pdf", "KR20150090348A.pdf", "KR20150093093A.pdf"]


def pages_and_chars(name):
    with pymupdf.open(CASE_0844 / name) as doc:
        return doc.page_count, sum(len(page.get_text()) for page in doc)


def refusal_stats(applications=None):
    decisions = [
        json.loads(line)
        for line in (PRECEDENTS / "kr_refusal_decisions.jsonl").open(encoding="utf-8")
    ]
    if applications is not None:
        decisions = [d for d in decisions if d["application"] in applications]
    responded = [d for d in decisions if d["responded"]]
    with_table = sum(d["has_unresolved_table"] for d in responded)
    return len(decisions), len(responded), with_table


def pct(part, whole):
    return f"{part / whole:.0%}" if whole else "-"


def main():
    print("[1] 사건 하나를 재 보니 74쪽 (0844 사건)")
    patent = pages_and_chars(PATENT)
    cites = [pages_and_chars(name) for name in CITATIONS]
    cite_pages = sum(p for p, _ in cites)
    total_chars = patent[1] + sum(c for _, c in cites)
    print(
        f"    특허 {patent[0]}쪽 + 인용발명 {len(CITATIONS)}건 {cite_pages}쪽"
        f" = {patent[0] + cite_pages}쪽, 약 {total_chars:,}자"
    )

    snapshot = json.loads((PRECEDENTS / "presentation_snapshot.json").read_text("utf-8"))
    apps = set(snapshot["applications"])
    current = r.load(r.KR_PATH)
    print("\n[2] 한국 55개 출원에서 대응 사례 164건")
    print(
        f"    발표 당시: {len(apps)}개 출원, {snapshot['cards']}건"
        f" (git show {snapshot['commit']}:data/precedents/kr_kipris_cases.jsonl)"
    )
    print(f"    지금 main: {len({c['application'] for c in current})}개 출원, {len(current)}건")

    manifest = json.loads((PRECEDENTS / "manifest.json").read_text("utf-8"))
    print("\n[3] 미국 1,019건")
    print(
        f"    {manifest['records']:,}건 ({manifest['applications']}개 출원 × 거절 종류)"
        " — data/precedents/manifest.json"
    )

    print("\n[4] 대응했는데 최종 거절된 건 중 '안 풀린 이유' 표를 적어 둔 비율")
    print("    (발표본 '22건 중 18건, 82%'는 KIPRIS 중복 응답 2건을 두 번 센 값)")
    for label, subset in (("발표 당시", apps), ("지금 main", None)):
        total, responded, with_table = refusal_stats(subset)
        print(
            f"    {label}: 거절결정 {total}건 중 대응한 {responded}건,"
            f" 그중 표 있음 {with_table}건 = {pct(with_table, responded)}"
        )

    us = r.stats("inventive_step")
    merge = next(a for a in us["by_argument"] if a["type"] == "dependent_merge")
    print("\n[5] 미국 진보성 거절 355건 중 68%가 풀림")
    print(
        f"    {us['resolved']}/{us['labeled']} = {pct(us['resolved'], us['labeled'])}"
        f" (제외 {us['excluded']}건 빼고)"
    )
    print("\n[6] 종속항 내용을 독립항에 합친 경우 81%")
    print(f"    {merge['resolved']}/{merge['cases']} = {pct(merge['resolved'], merge['cases'])}")


if __name__ == "__main__":
    main()
