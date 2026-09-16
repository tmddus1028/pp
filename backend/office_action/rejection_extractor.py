import re

from backend.analysis.citation_analyzer import extract_relied_citations, name_key
from backend.ingestion.adapters import evidence_at
from backend.office_action.oa_parser import (
    ACTION_START,
    Chunk,
    chunk_office_action,
    in_allowance_section,
)
from backend.patent.dependency_parser import parse_number_list
from backend.schemas import Document, Rejection

STATUTE = re.compile(
    r"(?:35\s*U\.?\s*S\.?\s*C\.?\s*(?:§+\s*)?|§+\s*)(101|102|103|112)"
    r"((?:\s*\([a-z0-9]+\))*)",
    re.I,
)


def normalize_statute(value: str) -> str:
    match = STATUTE.search(value)
    if not match:
        return "unknown"
    suffix = re.sub(r"\s+", "", match[2]).lower()
    return f"35 USC {match[1]}{suffix}"


def extract_local(document: Document, max_chars: int = 14000) -> tuple[list[Rejection], list[str]]:
    results = []
    warnings = [
        "로컬 규칙 모드: 표준 거절/지적 문장만 추출합니다. 문맥 해석과 누락 여부는 원문 확인이 필요합니다."
    ]
    for chunk in chunk_office_action(document, max_chars):
        extracted = extract_local_chunk(document, chunk)
        results.extend(extracted)
        if chunk.end - chunk.start >= max_chars:
            warnings.append(
                "긴 OA 구간이 분할되었습니다. 뒤쪽 설명/인용문헌이 누락되었는지 확인하세요."
            )
    if not results:
        warnings.append("명시적인 거절/지적을 추출하지 못했습니다. 거절이 없다는 뜻은 아닙니다.")
    resolve_prior_citations(results)
    return results, list(dict.fromkeys(warnings))


def resolve_prior_citations(rejections):
    """Resolve exact, unambiguous authors only with an explicit 'as applied ... above'."""
    definitions = {}
    for rejection in rejections:
        inherited = re.search(
            r"as\s+applied\s+to[\s\S]{0,350}?\bclaims?\s+[\d\s,–—-]+(?:and\s+\d+(?:-\d+)?)?\s+above",
            rejection.evidence.text,
            re.I,
        )
        for index, ref in enumerate(rejection.cited_references):
            key = name_key(ref.name) if ref.name else None
            if ref.type != "unknown" and key:
                definitions.setdefault(key, {})[ref.citation_id] = ref
            elif inherited and key and len(definitions.get(key, {})) == 1:
                original = next(iter(definitions[key].values()))
                rejection.cited_references[index] = original.model_copy(
                    update={
                        "evidence": ref.evidence,
                        "raw_text": ref.raw_text,
                        "citation_role": ref.citation_role,
                        "explicit_alias": ref.explicit_alias,
                        "definition_evidence": original.definition_evidence or original.evidence,
                    }
                )


def extract_local_chunk(document: Document, chunk: Chunk) -> list[Rejection]:
    results = []
    for match in ACTION_START.finditer(chunk.text):
        if match["action"].lower() == "rejected" and in_allowance_section(
            document, chunk.start + match.start()
        ):
            continue
        tail = chunk.text[match.start() :].rstrip()
        # A later withdrawal in the same section is not a current rejection.
        if re.search(r"\b(?:rejection|objection)\s+(?:is|has been)\s+withdrawn\b", tail, re.I):
            continue
        start = chunk.start + match.start()
        evidence = evidence_at(document, start, start + len(tail))
        header_end = re.search(r"\.\s+(?=[A-Z])|\n\s*\n", tail)
        header = tail[: header_end.end()] if header_end else tail
        # Limit statutes to the rejection's opening clause; later quoted law is not another ground.
        statutes = list(
            dict.fromkeys(normalize_statute(m[0]) for m in STATUTE.finditer(header))
        ) or ["unknown"]
        for statute in statutes:
            results.append(
                Rejection(
                    rejection_id="pending",
                    action_type="rejection"
                    if match["action"].lower() == "rejected"
                    else "objection",
                    statute=statute,
                    claims=parse_number_list(match["numbers"]),
                    reason_summary=header.strip(),
                    examiner_explanation=tail,
                    cited_references=extract_relied_citations(evidence, document)
                    if match["action"].lower() == "rejected"
                    else [],
                    evidence=evidence,
                    extraction_method="local",
                )
            )
    return results
