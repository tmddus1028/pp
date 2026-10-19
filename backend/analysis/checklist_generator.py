from backend.precedents import repository
from backend.precedents.taxonomy import REUSABLE, categorize
from backend.schemas import Impact, Rejection, ReviewItem

RESPONSE_LABELS = {"amendment": "보정 포함 대응", "argument_only": "보정 없이 주장만"}


def _percent(rate):
    return "–" if rate is None else f"{round(rate * 100)}%"


def precedent_item(rejection: Rejection, exclude_applications=frozenset()):
    """Checklist prompt backed by US response outcomes for the same common rejection type."""
    if rejection.action_type != "rejection":
        return None
    category = categorize(rejection.statute, None, rejection.examiner_explanation)
    if category not in REUSABLE:
        return None
    stats = repository.stats(category)
    if not stats["labeled"]:
        return None
    responses = ", ".join(
        f"{RESPONSE_LABELS[kind]} {_percent(group['rate'])}({group['cases']}건)"
        for kind, group in stats["by_response"].items()
        if group["cases"]
    )
    best = sorted(
        (a for a in stats["by_argument"] if a["cases"] >= 20),
        key=lambda a: a["rate"] or 0,
        reverse=True,
    )[:2]
    strong = "; ".join(f"{a['label']} {_percent(a['rate'])}({a['cases']}건)" for a in best)
    text = (
        f"[대응 사례] 같은 유형({stats['label']}) 미국 거절 {stats['labeled']}건 중 "
        f"{_percent(stats['resolved_rate'])}가 다음 조치에서 해소됐습니다 — {responses}."
    )
    if strong:
        text += f" 해소 비율이 높았던 대응: {strong}."
    if stats["reuse"] == "partial":
        text += " 한국·미국 요건 차이가 있어 대응 방식만 참고하세요."
    kr = repository.stats(category, repository.KR_PATH, exclude_applications)
    if kr["labeled"]:
        text += (
            f" 한국 실제 사건(KIPRIS) {kr['labeled']}건 중 해소 {kr['resolved']}건"
            f"(표본이 작아 사례로만 참고)."
        )
    text += " 참고용 통계이며 변리사 검토가 필요합니다."
    return text, {
        "category": category,
        "stats": stats,
        "cases": repository.find(category, rejection.examiner_explanation),
        "kr_stats": kr,
        "kr_cases": repository.find(
            category, path=repository.KR_PATH, exclude_applications=exclude_applications
        ),
    }


def generate_checklist(
    rejection: Rejection, impact: Impact, exclude_applications=frozenset()
) -> list[ReviewItem]:
    """Reproducible review prompts, not legal advice or proposed claim amendments."""
    items: list[tuple[list[int], str, dict | None]] = []
    for number in rejection.primary_claims or rejection.claims:
        items.append(
            (
                [number],
                f"Claim {number}: {rejection.statute} 지적 사유와 OA 근거를 대조하세요.",
                None,
            )
        )
    for ref in rejection.cited_references:
        label = ref.name or ref.publication_number or ref.citation_id
        items.append(
            (
                rejection.claims,
                f"{label}: 심사관이 인용한 내용과 해당 청구항의 구성요소 대응을 확인하세요.",
                None,
            )
        )
    if impact.dependency_impacted_claims:
        numbers = ", ".join(map(str, impact.dependency_impacted_claims))
        items.append(
            (
                impact.dependency_impacted_claims,
                f"종속 Claim {numbers}: 상위 청구항과 연결된 추가 검토 범위를 확인하세요.",
                None,
            )
        )
    if impact.missing_claims:
        items.append(
            (
                impact.missing_claims,
                "OA가 지적한 청구항 일부가 입력에 없습니다. OA 당시의 청구항 버전을 확인하세요.",
                None,
            )
        )
    precedent = precedent_item(rejection, exclude_applications)
    if precedent:
        items.append((rejection.claims, *precedent))
    return [
        ReviewItem(
            item_id=f"{rejection.rejection_id}-T{i}",
            rejection_id=rejection.rejection_id,
            claim_numbers=numbers,
            text=text,
            evidence=rejection.evidence,
            precedent=basis,
        )
        for i, (numbers, text, basis) in enumerate(items, 1)
    ]
