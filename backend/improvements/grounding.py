"""Mechanical source checks; not semantic or legal certification."""

import re


def numeric_terms(text):
    return re.findall(
        r"(?<![\w])(?:below|above|under|over|less than|greater than|at least|at most)?\s*\d+(?:\.\d+)?(?:\s*[-–~]\s*\d+(?:\.\d+)?)?\s*(?:°\s*[CF]|Hz|nm|mm|cm|%|℃|도|이하|이상|미만|초과)?",
        text,
        re.I,
    )


def normalized(text):
    return re.sub(r"\s+", "", text).casefold()


def verify_quantities(proposed, original, quoted):
    known = {normalized(n) for n in numeric_terms(original + " " + quoted)}
    for number in numeric_terms(proposed):
        if re.search(r"[A-Za-z°%℃가-힣]", number) and normalized(number) not in known:
            raise ValueError(
                "제안한 수치·범위가 원 청구항 또는 명세서 인용문에서 확인되지 않습니다."
            )


def verify_source_mentions(text, context):
    ids = {s["evidence_id"] for s in context["sources"]}
    for eid in re.findall(r"\b(?:SPEC|OA|CITE|CLAIM|PARENT)-[A-Za-z0-9-]+", text):
        if eid not in ids:
            raise ValueError("설명에 제공되지 않은 근거 ID가 있습니다.")
    source_text = " ".join(s["evidence"]["text"] for s in context["sources"])
    for paragraph in re.findall(r"\[\s*(\d{4,5})\s*\]", text):
        if not re.search(r"\[\s*" + paragraph + r"\s*\]", source_text):
            raise ValueError("설명에 제공되지 않은 명세서 문단 번호가 있습니다.")
