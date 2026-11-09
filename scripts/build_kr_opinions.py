"""Attach the applicant's 의견서 text (downloaded by hand from 특허청 OPD) to the KIPRIS cases.

Reads data/research/kr_{application}/opinion_{YYYYMMDD}.pdf (see OPINION_DOWNLOAD_TODO.md) and
writes data/precedents/kr_opinions.jsonl keyed by case_id:

  opinion_date        filing date of the 의견서 (from the file name)
  opinion_file        the PDF it came from (repo-relative)
  applicant_argument  the applicant's own conclusion (소결/결론 paragraphs), for cards and prompts
  opinion_text        the whole 의견내용 body, line wraps joined

One 의견서 answers every rejection of its notice, so it is attached to each case of that
application whose notice came before the filing and whose next action came after it.

Usage: uv run python scripts/build_kr_opinions.py
"""

import json
import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.precedents.repository import KR_PATH, load  # noqa: E402

RESEARCH = ROOT / "data/research"
OUT = ROOT / "data/precedents/kr_opinions.jsonl"
MAX_TEXT = 20000
MAX_ARGUMENT = 900
# Lines that start a new block even when the previous line ran to the margin.
BLOCK_START = re.compile(
    r"^([ⅠⅡⅢⅣⅤⅥⅦⅰⅱⅲⅳⅴ]|[IVX]{1,4}\.|\d+\.|\(\d+\)|[가-하]\.|[①-⑳]|『|\[청구항|인용발명\s*\d|-\s*아\s*래)"
)
# Headings whose paragraphs state the applicant's conclusion on the rejection.
CONCLUSION = re.compile(r"^(\S{0,4}\.?\s*)?(소\s*결|정리하면|결론적으로|요컨대)")
CLOSING = re.compile(r"^(\S{0,3}\.?\s*)?(결\s*어|결\s*론|맺음말)\s*$")


def body(path):
    """The 의견내용 attachment: everything after the cover form."""
    text = "\n".join(page.get_text() for page in pymupdf.open(path))
    parts = re.split(r"\n\s*의견\s*내용\s*\n", text)
    return parts[-1] if len(parts) > 1 else text


def unwrap(text):
    """Join lines the PDF wrapped at the margin; keep real paragraph breaks.

    KIPO PDFs wrap by character, so a space that fell on the wrap is lost; tolerable for reading.
    """
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    lengths = sorted(len(line) for line in lines)
    width = lengths[int(len(lengths) * 0.75)] if lengths else 0  # most lines run to the margin
    out, prev = [], ""
    for line in lines:
        if out and len(prev) >= width * 0.8 and not BLOCK_START.match(line):
            out[-1] += line
        else:
            out.append(line)
        prev = line
    return "\n".join(out)


def argument(text):
    """소결/결론 paragraphs (the applicant's own summary); else the paragraphs before 결어."""
    lines = text.split("\n")
    picked, taking = [], False
    for line in lines:
        if CONCLUSION.match(line):
            taking = True
            rest = CONCLUSION.sub("", line).strip(" .:")
            if rest:
                picked.append(rest)
            continue
        if taking and BLOCK_START.match(line) and len(" ".join(picked)) >= 200:
            taking = False
        if CLOSING.match(line):
            break
        if taking:
            picked.append(line)
    if not picked:  # last whole sentences before 결어 (the window's first one may be cut)
        end = next((i for i, line in enumerate(lines) if CLOSING.match(line)), len(lines))
        window = " ".join(lines[max(0, end - 8) : end])
        sentences = [s for s in re.split(r"(?<=다\.)\s*", window) if s.strip()]
        picked = sentences[1:][-3:] or sentences[-3:]
    joined = " ".join(picked).lstrip(" ,.")
    return joined[:MAX_ARGUMENT].rstrip() + ("…" if len(joined) > MAX_ARGUMENT else "")


def compact(date):
    return date.replace("-", "")


def main():
    cases = load(KR_PATH)
    rows, unmatched = [], []
    for pdf in sorted(RESEARCH.glob("kr_*/opinion_*.pdf")):
        application = pdf.parent.name.removeprefix("kr_")
        filed = pdf.stem.removeprefix("opinion_")[:8]
        hits = [
            c
            for c in cases
            if c["application"] == application
            and compact(c["oa_date"]) < filed <= compact(c["next_action_date"] or "99999999")
        ]
        if not hits:
            unmatched.append(pdf.relative_to(ROOT).as_posix())
            continue
        text = unwrap(body(pdf))
        record = {
            "opinion_date": f"{filed[:4]}-{filed[4:6]}-{filed[6:]}",
            "opinion_file": pdf.relative_to(ROOT).as_posix(),
            "applicant_argument": argument(text),
            "opinion_text": text[:MAX_TEXT],
        }
        rows += [{"case_id": c["case_id"], **record} for c in hits]
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    pdfs = len({r["opinion_file"] for r in rows})
    print(f"{pdfs} 의견서 → {len(rows)} cases → {OUT.relative_to(ROOT)}")
    for path in unmatched:
        print("no case for", path)


if __name__ == "__main__":
    main()
