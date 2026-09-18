"""Explicit Korean dispositions; silence is not allowance."""

import re

from .ingestion import evidence_at
from .models import ClaimStatus, ReviewError


def extract_statuses(claims, rejections, document):
    from .parsers import claim_numbers

    result = {}
    for c in claims:
        r = next((r for r in rejections if c.number in r.claims), None)
        status = "canceled" if c.status == "canceled" else "rejected" if r else "unknown"
        result[c.number] = ClaimStatus(
            claim_number=c.number,
            status=status,
            raw_status=r.statute if r else "삭제" if c.status == "canceled" else "",
            evidence=r.evidence if r else c.evidence if c.status == "canceled" else None,
        )
    expressions = [
        ("allowable", r"특허\s*가능한\s*청구항\s*[:：]\s*"),
        ("pending", r"심사\s*대상\s*청구항\s*[:：]\s*"),
        ("withdrawn", r"철회된\s*청구항\s*[:：]\s*"),
        ("canceled", r"삭제된\s*청구항\s*[:：]\s*"),
        ("amended", r"보정된\s*청구항\s*[:：]\s*"),
        ("objected", r"보정이\s*필요한\s*청구항\s*[:：]\s*"),
    ]
    for status, pattern in expressions:
        for m in re.finditer(
            pattern + r"((?:청구항\s*)?제?\s*\d+[\d\s항제,내지및~∼–—-]*)", document.text
        ):
            for n in claim_numbers(m[1]):
                if n not in result:
                    raise ReviewError(f"청구항 상태 표의 {n}항이 입력 청구범위에 없습니다.")
                current = result[n]
                if status == "pending" and current.status != "unknown":
                    continue
                if status == "allowable" and current.status == "rejected":
                    raise ReviewError(f"청구항 {n}의 거절/특허 가능 상태가 충돌합니다.")
                result[n] = ClaimStatus(
                    claim_number=n,
                    status=status,
                    raw_status=m[0],
                    evidence=evidence_at(document, m.start(), m.end()),
                )
    return list(result.values())
