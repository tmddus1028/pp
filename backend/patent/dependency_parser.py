import re

import networkx as nx

from backend.errors import DocumentError
from backend.schemas import Claim

NUMBER_LIST = r"\d+(?:\s*(?:[-–—]|\bto\b|\bthrough\b)\s*\d+)?(?:\s*(?:,\s*(?:(?:and|or)\s+)?|\band\b\s*|\bor\b\s*)\d+(?:\s*(?:[-–—]|\bto\b|\bthrough\b)\s*\d+)?)*"
CLAIM_REFERENCE = re.compile(r"\bclaims?(?:\(s\))?\s+(?P<numbers>" + NUMBER_LIST + r")", re.I)


def parse_number_list(value: str) -> list[int]:
    if not re.fullmatch(NUMBER_LIST, value.strip(), re.I):
        raise DocumentError(f"청구항 번호 범위를 해석할 수 없습니다: {value[:100]}")
    numbers: set[int] = set()
    for item in re.finditer(r"(\d+)(?:\s*(?:[-–—]|\bto\b|\bthrough\b)\s*(\d+))?", value, re.I):
        low, high = int(item[1]), int(item[2] or item[1])
        if low < 1 or high < low or high > 10000 or high - low > 1000:
            raise DocumentError("청구항 번호 범위가 유효하지 않거나 너무 큽니다.")
        numbers.update(range(low, high + 1))
    return sorted(numbers)


def parse_dependencies(text: str) -> list[int]:
    return sorted(
        {n for match in CLAIM_REFERENCE.finditer(text) for n in parse_number_list(match["numbers"])}
    )


def build_dependency_graph(claims: list[Claim]) -> tuple[nx.DiGraph, list[str]]:
    graph = nx.DiGraph()
    warnings = []
    active = {c.claim_number for c in claims if c.status == "active"}
    graph.add_nodes_from(active)
    for claim in claims:
        if claim.status == "canceled":
            continue
        for parent in claim.depends_on:
            if parent == claim.claim_number:
                raise DocumentError(f"Claim {parent}가 자기 자신에 종속됩니다.")
            if parent not in active:
                warnings.append(
                    f"Claim {claim.claim_number}의 부모 Claim {parent}가 없거나 취소되었습니다."
                )
                continue
            if parent > claim.claim_number:
                warnings.append(
                    f"Claim {claim.claim_number}가 뒤 번호 Claim {parent}를 참조합니다. 원문을 확인하세요."
                )
            graph.add_edge(parent, claim.claim_number)
    if not nx.is_directed_acyclic_graph(graph):
        raise DocumentError("청구항 종속관계에 순환이 있습니다. 입력 청구항을 확인하세요.")
    return graph, warnings
