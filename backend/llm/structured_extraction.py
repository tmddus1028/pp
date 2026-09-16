import re

from backend.analysis.citation_analyzer import (
    PUBLICATION,
    citation_id,
    extract_relied_citations,
    name_key,
    normalize_publication,
)
from backend.errors import ExtractionError
from backend.ingestion.adapters import evidence_at
from backend.llm.client import ExtractionClient, RejectionDraft
from backend.office_action.oa_parser import (
    ACTION_START,
    Chunk,
    chunk_office_action,
    in_allowance_section,
)
from backend.office_action.rejection_extractor import STATUTE, normalize_statute
from backend.patent.dependency_parser import parse_number_list
from backend.schemas import CitedReference, Document, Rejection


def validate_draft(
    draft: RejectionDraft, chunk: Chunk, document: Document, provider: str
) -> Rejection:
    start = chunk.text.find(draft.evidence)
    if not draft.evidence.strip() or start < 0 or chunk.text.count(draft.evidence) != 1:
        raise ExtractionError("LLM 근거 문장이 원문 위치와 일치하지 않습니다.")
    # Exact-match predicate when recognized; otherwise require an explicit claim expression
    # and action word. This permits nonstandard grammar while preventing bare number invention.
    actions = [
        m
        for m in ACTION_START.finditer(draft.evidence)
        if (m["action"].lower() == "rejected") == (draft.action_type == "rejection")
    ]
    mentioned = {n for m in actions for n in parse_number_list(m["numbers"])}
    if not draft.claims or not set(draft.claims) <= mentioned or min(draft.claims) <= 0:
        raise ExtractionError("LLM이 근거에 없는 직접 지적 Claim 번호를 반환했습니다.")
    if draft.action_type == "rejection" and in_allowance_section(document, chunk.start + start):
        raise ExtractionError("허용 관련 섹션을 새로운 거절로 해석했습니다.")
    predicate = (
        r"\breject(?:ed|ion)\b" if draft.action_type == "rejection" else r"\bobject(?:ed|ion)\b"
    )
    if not re.search(predicate, draft.evidence, re.I):
        raise ExtractionError("거절/지적 유형을 근거에서 확인할 수 없습니다.")
    if re.search(r"\b(?:not rejected|no rejection|rejection is withdrawn)\b", draft.evidence, re.I):
        raise ExtractionError("부정되거나 철회된 거절을 현재 거절로 해석했습니다.")
    statute = normalize_statute(draft.statute)
    supported = {normalize_statute(m[0]) for m in STATUTE.finditer(draft.evidence)}
    if statute != "unknown" and statute not in supported:
        raise ExtractionError("LLM 법조항이 근거 원문에 없습니다.")
    evidence = evidence_at(document, chunk.start + start, chunk.start + start + len(draft.evidence))
    refs = []
    for ref in draft.cited_references:
        if not ref.evidence.strip() or ref.evidence not in draft.evidence:
            raise ExtractionError("인용문헌의 근거가 거절 근거에 포함되지 않습니다.")
        if ref.name and ref.name.casefold() not in ref.evidence.casefold():
            raise ExtractionError("인용문헌 이름이 근거에 없습니다.")
        publication = normalize_publication(ref.publication_number)
        if ref.publication_number and (
            not publication
            or publication
            not in {normalize_publication(m[0]) for m in PUBLICATION.finditer(ref.evidence)}
        ):
            raise ExtractionError("인용문헌 공개번호가 근거에 없습니다.")
        if not ref.name and not publication:
            continue
        ref_start = evidence.start + draft.evidence.index(ref.evidence)
        refs.append(
            CitedReference(
                citation_id=citation_id(
                    ref.name, publication, f"{evidence.document_id}:{evidence.start}"
                ),
                name=ref.name,
                publication_number=publication,
                evidence=evidence_at(document, ref_start, ref_start + len(ref.evidence)),
            )
        )
    # Complete explicit bibliographic references locally after validating every
    # model-provided reference. Use the existing action-bounded chunk only when
    # it contains one action; do not borrow citations from adjacent rejections.
    chunk_actions = list(ACTION_START.finditer(chunk.text))
    source = evidence
    if len(chunk_actions) == 1 and (
        evidence.start <= chunk.start + chunk_actions[0].start() < evidence.end
    ):
        source = evidence_at(document, chunk.start, chunk.end)
    explicit = (
        extract_relied_citations(source, document) if draft.action_type == "rejection" else []
    )
    merged_refs = {ref.citation_id: ref for ref in explicit}
    for ref in refs:
        if ref.citation_id in merged_refs:
            continue
        if not any(
            other.publication_number == ref.publication_number
            and ref.publication_number
            or other.name
            and ref.name
            and name_key(other.name) == name_key(ref.name)
            for other in explicit
        ):
            raise ExtractionError("인용문헌이 실제 거절의 relied-upon 문헌으로 확인되지 않습니다.")
        if (
            not ref.publication_number
            and ref.name
            and any(
                other.name
                and name_key(other.name) == name_key(ref.name)
                and other.evidence.start < ref.evidence.end
                and ref.evidence.start < other.evidence.end
                for other in explicit
            )
        ):
            continue
        merged_refs[ref.citation_id] = ref
    refs = sorted(merged_refs.values(), key=lambda ref: ref.evidence.start)
    return Rejection(
        rejection_id="pending",
        action_type=draft.action_type,
        statute=statute,
        claims=sorted(set(draft.claims)),
        reason_summary=draft.reason_summary,
        examiner_explanation=draft.examiner_explanation,
        cited_references=refs,
        evidence=evidence,
        extraction_method=provider,
    )


def extract_structured(
    document: Document, client: ExtractionClient, provider: str, max_chars: int = 14000
) -> tuple[list[Rejection], list[str]]:
    rejections, warnings = [], []
    for chunk in chunk_office_action(document, max_chars):
        if len(chunk.text) >= max_chars:
            warnings.append(
                "긴 OA 구간이 분할되었습니다. 이어지는 설명/인용문헌이 누락되었는지 확인하세요."
            )
        for draft in client.extract(chunk.text).rejections:
            # Fail visibly on unsupported content; never quietly turn invalid output into success.
            rejections.append(validate_draft(draft, chunk, document, provider))
    if not rejections:
        warnings.append(
            "LLM이 명시적 거절/지적을 추출하지 못했습니다. 원문과 추출 누락을 확인하세요."
        )
    return rejections, list(dict.fromkeys(warnings))


def merge_rejections(rejections: list[Rejection]) -> list[Rejection]:
    merged: list[Rejection] = []
    for item in sorted(rejections, key=lambda r: (r.evidence.start, r.statute)):
        key = (
            item.action_type,
            item.statute,
            tuple(item.claims),
            tuple(sorted(r.citation_id for r in item.cited_references)),
        )
        duplicate = next(
            (
                r
                for r in merged
                if (
                    r.action_type,
                    r.statute,
                    tuple(r.claims),
                    tuple(sorted(c.citation_id for c in r.cited_references)),
                )
                == key
                and r.evidence.start < item.evidence.end
                and item.evidence.start < r.evidence.end
            ),
            None,
        )
        if duplicate is None:
            merged.append(item)
    return [r.model_copy(update={"rejection_id": f"R{i}"}) for i, r in enumerate(merged, 1)]
