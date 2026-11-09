"""Write data/research/OPINION_DOWNLOAD_TODO.md: 의견서 PDFs to fetch by hand from 특허청 OPD.

uv run python scripts/opinion_todo.py

KIPRIS Plus has no 의견서 text, and OPD asks for a CAPTCHA per document, so the team downloads
them manually. Targets: 진보성(제29조제2항) responses that ended in 등록결정 — the cases PinPoint
shows as "이렇게 대응해서 등록됐다". 채점표 cases come first. Already-saved files are checked,
so re-running after downloads (or after the case data grows) keeps the list current.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.precedents.kipris import Kipris, KiprisError  # noqa: E402
from backend.precedents.repository import KR_PATH, load  # noqa: E402

OUT = ROOT / "data/research/OPINION_DOWNLOAD_TODO.md"
RESEARCH = ROOT / "data/research"
OPD = (
    "https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do"
    "?paramType=A&cntry=KR&appno={app}&code=A&docgrp=ALL&from=K"
)


def dotted(ymd):
    return f"{ymd[:4]}.{ymd[4:6]}.{ymd[6:8]}"


def filing_dates(api, app, start, end):
    """보정서 receipt dates in (start, end]; the 의견서 is filed the same day."""
    try:
        items = api.items("CL", "amendmentHistoryInfo", app)
    except KiprisError:
        return []
    return sorted(
        {
            i["receiptSendDate"]
            for i in items
            if "보정" in i["receiptSendDocumentName"] and start < i["receiptSendDate"] <= end
        }
    )


def targets():
    gold = {p.stem for p in (ROOT / "data/eval/kr").glob("*.json")}
    seen, rows = set(), []
    for c in load(KR_PATH):
        key = (c["application"], c["oa_date"])
        if c["category"] != "inventive_step" or c["next_action"] != "등록결정" or key in seen:
            continue
        seen.add(key)
        rows.append({**c, "gold": c["application"] in gold})
    return sorted(rows, key=lambda c: (not c["gold"], c["application"], c["oa_date"]))


def main():
    api = Kipris()
    rows = targets()
    lines = []
    done = 0
    for c in rows:
        app = c["application"]
        start, end = c["oa_date"].replace("-", ""), c["next_action_date"].replace("-", "")
        dates = filing_dates(api, app, start, end)
        if dates:
            when, stamp = dotted(dates[-1]), dates[-1]
        else:
            when, stamp = f"{dotted(start)}~{dotted(end)} 사이", "YYYYMMDD"
        folder = RESEARCH / f"kr_{app}"
        saved = sorted(folder.glob("opinion_*.pdf")) if folder.exists() else []
        hit = [p for p in saved if stamp == "YYYYMMDD" or stamp in p.name]
        done += bool(hit)
        kind = "재심사 의견서" if c["oa_type"] == "거절결정서" else "의견서"
        tags = " · ⭐채점표" if c["gold"] else ""
        lines.append(
            f"- [{'x' if hit else ' '}] **{app[:2]}-{app[2:6]}-{app[6:]}** · {kind} · "
            f"제출일 {when}{tags} · "
            f"[OPD 열기]({OPD.format(app=app[2:] if app.startswith('10') else app)}) → "
            f"`data/research/kr_{app}/opinion_{stamp}.pdf`"
        )
    header = f"""# 의견서 다운로드 체크리스트

PinPoint가 보여 주는 "이렇게 대응해서 등록됐다" 사례의 **출원인 주장(의견서 본문)** 을 채우기 위한 목록입니다.
KIPRIS API에는 의견서 본문이 없고, 특허청 OPD는 문서마다 보안문자(CAPTCHA)를 넣어야 해서 손으로 받습니다.

- 대상: **진보성(제29조제2항) 거절 → 대응 → 등록결정** {len(rows)}건. 위에서부터 순서대로 (⭐채점표 사건이 맨 위)
- 진행: **{done} / {len(rows)}건 완료** (건당 1~2분)

## 받는 방법 (한 건당)
1. `OPD 열기` 클릭
2. 목록에서 **제출일 날짜의 `의견(답변, 소명)서`** 줄 → **원문** 클릭 (같은 날 `보정서`는 안 받아도 됨)
3. 보안문자 입력 → PDF 다운로드
4. 화살표 뒤 경로에 그 이름 그대로 저장 (폴더가 없으면 만들기)
   - 제출일이 "~사이"로 나온 건: 그 기간에 있는 의견서 날짜를 파일 이름 `YYYYMMDD` 자리에 넣기

## 다 받은 뒤 (또는 중간에 끊을 때)
1. `uv run python scripts/opinion_todo.py` → 받은 건이 자동으로 [x]
2. `git add data/research` → 커밋 → 푸시

## 목록
"""
    OUT.write_text(header + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(rows)} targets, {done} done → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
