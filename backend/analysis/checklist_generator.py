from backend.schemas import Impact, Rejection, ReviewItem


def generate_checklist(rejection: Rejection, impact: Impact) -> list[ReviewItem]:
    """Reproducible review prompts, not legal advice or proposed claim amendments."""
    items: list[tuple[list[int], str]] = []
    for number in rejection.primary_claims or rejection.claims:
        items.append(
            ([number], f"Claim {number}: {rejection.statute} 지적 사유와 OA 근거를 대조하세요.")
        )
    for ref in rejection.cited_references:
        label = ref.name or ref.publication_number or ref.citation_id
        items.append(
            (
                rejection.claims,
                f"{label}: 심사관이 인용한 내용과 해당 청구항의 구성요소 대응을 확인하세요.",
            )
        )
    if impact.dependency_impacted_claims:
        numbers = ", ".join(map(str, impact.dependency_impacted_claims))
        items.append(
            (
                impact.dependency_impacted_claims,
                f"종속 Claim {numbers}: 상위 청구항과 연결된 추가 검토 범위를 확인하세요.",
            )
        )
    if impact.missing_claims:
        items.append(
            (
                impact.missing_claims,
                "OA가 지적한 청구항 일부가 입력에 없습니다. OA 당시의 청구항 버전을 확인하세요.",
            )
        )
    return [
        ReviewItem(
            item_id=f"{rejection.rejection_id}-T{i}",
            rejection_id=rejection.rejection_id,
            claim_numbers=numbers,
            text=text,
            evidence=rejection.evidence,
        )
        for i, (numbers, text) in enumerate(items, 1)
    ]
