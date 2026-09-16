import networkx as nx

from backend.office_action.claim_status import TERMINAL
from backend.patent.dependency_parser import build_dependency_graph
from backend.schemas import Impact, Patent, Rejection


def analyze_impacts(patent: Patent, rejections: list[Rejection], statuses=()) -> list[Impact]:
    graph, _ = build_dependency_graph(patent.claims)
    impacts = []
    excluded = {s.claim_number for s in statuses if s.status in TERMINAL}
    for rejection in rejections:
        addressed = set(rejection.claims) - excluded
        direct = addressed if rejection.action_type == "rejection" else set()
        present = direct.intersection(graph.nodes)
        affected = set().union(*(nx.descendants(graph, n) for n in present)) if present else set()
        rejection.primary_claims = sorted(
            n for n in present if not nx.ancestors(graph, n) & present
        )
        impacts.append(
            Impact(
                rejection_id=rejection.rejection_id,
                direct_claims=sorted(direct),
                objected_claims=sorted(addressed) if rejection.action_type == "objection" else [],
                dependency_impacted_claims=sorted(affected - direct - excluded),
                missing_claims=sorted(direct - present),
                citations=sorted({c.citation_id for c in rejection.cited_references}),
            )
        )
    return impacts
