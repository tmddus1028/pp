"""Baseline for "보정 재료 찾기": without AI, how much of the really-added limitation is in our top-k candidates?

For claim 1 of each first-response case that was resolved by amendment (data/eval/outcome/cases.jsonl):
  gold        the text added to claim 1 in that response (repository added_limitation)
  candidates  its dependent claims in claim order, then specification paragraphs ranked by overlap
              with claim 1 (no LLM, no cited-reference check yet)
Score = share of the gold text's character 3-grams found in the union of the top-k candidates.
"hit" = at least half of it. Publications come from Google Patents (cached in data/outputs/material/).

uv run python scripts/material_eval.py            # fetch what is missing, then score
uv run python scripts/material_eval.py --offline  # score cached publications only
"""

import argparse
import html
import json
import math
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from build_gold_cases import UA, google_publication  # noqa: E402

from backend.precedents import repository  # noqa: E402
from korean_prototype.kr_review.parsers import DEPENDENCY, claim_numbers  # noqa: E402

CACHE = ROOT / "data/outputs/material"
KS = (1, 3, 5, 10)
HIT = 0.5


def grams(text):
    s = re.sub(r"[\W_]+", "", text)  # Hangul counts as a word character, so only spaces/punctuation go
    return {s[i : i + 3] for i in range(len(s) - 2)}


def coverage(gold, texts):
    g = grams(gold)
    return len(g & set().union(*map(grams, texts))) / len(g) if g else 0.0


def strip(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def parents(text):
    """Claim numbers a Korean claim refers to ("제1항에 있어서", "청구항 1 또는 2에 따른"), same rule as the app."""
    m = DEPENDENCY.search(text)
    try:
        return claim_numbers(m[1]) if m else []
    except Exception:  # noqa: BLE001 - an odd reference just makes the claim look independent
        return []


def parse(page):
    """Claims {n: (text, parents)} and description paragraphs [(num, text)] from a Google Patents page."""
    claims = {}
    for n, body in re.findall(r'<div num="(\d+)" class="claim">(.*?)</div>\s*</div>', page, re.S):
        text = strip(body)
        claims[int(n)] = (text, [p for p in parents(text) if p < int(n)])
    paras = re.findall(r'<div num="(\d+)" class="description-paragraph">(.*?)</div>', page, re.S)
    return claims, [(num, strip(body)) for num, body in paras]


def descendants(claims, root=1):
    """Claims that depend on root directly or through other claims, in claim order."""
    found = {root}
    for n in sorted(claims):  # parents always have smaller numbers
        if any(p in found for p in claims[n][1]):
            found.add(n)
    return sorted(found - {root})


def rank_spec(claim1, paras):
    c = grams(claim1)
    def score(p):
        g = grams(p)
        return len(g & c) / math.sqrt(len(g) * len(c)) if g and c else 0.0
    return sorted((t for _, t in paras), key=score, reverse=True)


def fetch(app, offline):
    path = CACHE / f"{app}.html"
    if not path.exists():
        if offline:
            return None
        pub, _ = google_publication(app)
        page = httpx.get(f"https://patents.google.com/patent/{pub}/ko", headers=UA, timeout=30).text
        path.write_text(page, encoding="utf-8")
        time.sleep(1)  # be polite to Google Patents
    return path.read_text(encoding="utf-8")


def check():
    assert coverage("가나다라마", ["xx가나다라마yy"]) == 1.0
    assert coverage("가나다라마", ["무관한문장"]) == 0.0
    toy = {1: ("", []), 2: ("", [1]), 3: ("", [2]), 4: ("", []), 5: ("", [4])}
    assert descendants(toy) == [2, 3]
    assert parents("제1항에 있어서, 상기") == [1]
    assert parents("청구항 1 또는 청구항 2에 따른 방법") == [1, 2]
    assert parents("자원 지시 방법으로서") == []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    check()
    CACHE.mkdir(parents=True, exist_ok=True)

    db = {c["case_id"]: c for c in repository.real_cases()}
    rows = [json.loads(line) for line in (ROOT / "data/eval/outcome/cases.jsonl").open(encoding="utf-8")]
    rows = [
        r
        for r in rows
        if r.get("outcome") == "resolved"
        and r.get("method") in ("merge", "spec")
        and db.get(r["case_id"], {}).get("added_limitation")
    ]

    results, skipped = [], defaultdict(list)
    for r in rows:
        app = r["application"]
        try:
            page = fetch(app, args.offline)
        except Exception as exc:  # noqa: BLE001 - one missing publication should not stop the run
            skipped["fetch"].append(f"{app}: {exc}")
            continue
        if page is None:
            skipped["not cached"].append(app)
            continue
        claims, paras = parse(page)
        if 1 not in claims or not paras:
            skipped["parse"].append(app)
            continue
        claim1 = claims[1][0]
        # The publication's claim 1 must be the one the examiner rejected, or the gold diff means nothing.
        if coverage(r["claim_before"], [claim1]) < 0.8:
            skipped["claim 1 differs from the notice"].append(app)
            continue
        gold = db[r["case_id"]]["added_limitation"]
        deps = [claims[n][0] for n in descendants(claims)]
        spec = rank_spec(claim1, paras)
        lists = {"deps": deps, "spec": spec, "deps+spec": deps + spec}
        results.append(
            {
                "application": app,
                "method": r["method"],
                "dependents": len(deps),
                "paragraphs": len(paras),
                "ceiling": {name: round(coverage(gold, items), 3) for name, items in lists.items()},
                "at": {
                    name: {k: round(coverage(gold, items[:k]), 3) for k in KS} for name, items in lists.items()
                },
            }
        )
        print(f"{app} {r['method']:5} deps {len(deps):2} paras {len(paras):3} ceiling {results[-1]['ceiling']}")

    (CACHE / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    for reason, apps in skipped.items():
        print(f"skipped ({reason}): {len(apps)}")

    print(f"\nscored {len(results)} cases · hit = coverage ≥ {HIT}")
    for method in ("merge", "spec", "all"):
        rs = [x for x in results if method == "all" or x["method"] == method]
        if not rs:
            continue
        print(f"\n[{method}] n={len(rs)}")
        print(f"{'list':10} " + " ".join(f"{'@' + str(k):>12}" for k in KS) + f" {'ceiling':>12}")
        for name in ("deps", "spec", "deps+spec"):
            cells = []
            for k in KS:
                cov = [x["at"][name][k] for x in rs]
                cells.append(f"{sum(c >= HIT for c in cov) / len(rs):>5.0%} ({sum(cov) / len(rs):.2f})")
            ceil = [x["ceiling"][name] for x in rs]
            cells.append(f"{sum(c >= HIT for c in ceil) / len(rs):>5.0%} ({sum(ceil) / len(rs):.2f})")
            print(f"{name:10} " + " ".join(f"{c:>12}" for c in cells))


if __name__ == "__main__":
    main()
