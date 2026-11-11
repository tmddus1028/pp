"""Statistics over every Korean 의견제출통지서 1999–2022 (KIPRISPlus 학습데이터, 333만 건).

uv run python scripts/build_kr_oa_stats.py PATH/notices.jsonl.gz
  → data/precedents/kr_oa_dataset_stats.json (numbers only, committed)

The source is the official pickle (op_final_parsing_dict.p), converted to one JSON line per notice
without unpickling. It has the notice text, the examiner's 구성 대비 tables and the citations,
but no outcomes, claims or IPC, so these numbers describe rejections, not what worked.
"""

import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.precedents.taxonomy import categorize  # noqa: E402

OUT = ROOT / "data/precedents/kr_oa_dataset_stats.json"
LAW = re.compile(
    r"특허법\s*(?:제\s*)?\d+\s*조(?:\s*의\s*\d+)?(?:\s*제?\s*\d+\s*항)?(?:\s*(?:제\s*)?\d+\s*호)?"
)
ATTACHMENT = re.compile(r"첨부\s*\d+\s*([^\n]+)")
COUNTRY = [
    ("일본", r"일본|JP"),
    ("미국", r"미국|US"),
    ("유럽", r"유럽|EP"),
    ("국제(WO)", r"국제|WO|PCT"),
    ("중국", r"중국|CN"),
    ("한국", r"한국|대한민국|공개특허|등록특허|등록실용|공개실용|KR|10-\d{4}-\d{7}"),
]


def text(value):
    if isinstance(value, list):
        return "\n".join(map(text, value))
    return value if isinstance(value, str) else ""


def country(line):
    return next((name for name, pattern in COUNTRY if re.search(pattern, line)), "기타·비특허")


def main():
    years, categories, per_notice, countries = Counter(), Counter(), Counter(), Counter()
    notices_per_app, apps = Counter(), Counter()
    n = tables = with_citations = 0
    for line in gzip.open(sys.argv[1], "rt", encoding="utf-8"):
        notice = json.loads(line)
        n += 1
        year = str(notice.get("SendDate", ""))[:4]
        years[year] += 1
        apps[notice["app"]] += 1
        body = text(notice.get("RejectionContent")) + "\n" + text(notice.get("RejectionLawDetail"))
        laws = text(notice.get("ExaminationResult")) + "\n" + body
        found = {categorize(m) for m in LAW.findall(laws)} - {"other", None}
        categories.update(found or {"unknown"})
        detail = text(notice.get("RejectionLawDetail"))
        tables += "<Table" in detail and "인용발명" in detail
        cited = ATTACHMENT.findall(text(notice.get("AttachmentContent")))
        per_notice[min(len(cited), 6)] += 1
        with_citations += bool(cited)
        countries.update(country(c) for c in cited)
        if n % 500_000 == 0:
            print(f"{n:,}", flush=True)
    notices_per_app.update(min(c, 4) for c in apps.values())
    total_cited = sum(countries.values())
    stats = {
        "source": "KIPRISPlus 의견제출통지서 학습데이터 (op_final_parsing_dict.p)",
        "applications": len(apps),
        "notices": n,
        "years": dict(sorted(years.items())),
        "notices_per_application": {
            ("4+" if k == 4 else str(k)): v for k, v in sorted(notices_per_app.items())
        },
        "rejection_categories": {k: [v, round(v / n, 3)] for k, v in categories.most_common()},
        "with_citations": [with_citations, round(with_citations / n, 3)],
        "citations_per_notice": {
            ("6+" if k == 6 else str(k)): v for k, v in sorted(per_notice.items())
        },
        "citations_total": total_cited,
        "citation_countries": {
            k: [v, round(v / total_cited, 3)] for k, v in countries.most_common()
        },
        "examiner_comparison_tables": [tables, round(tables / n, 3)],
    }
    OUT.write_text(
        json.dumps(stats, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
