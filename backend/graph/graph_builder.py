from backend.analysis.citation_analyzer import reference_label
from backend.schemas import Graph, GraphEdge, GraphNode, Impact, Patent, Rejection


def build_graph(
    patent: Patent, rejections: list[Rejection], impacts: list[Impact], statuses=()
) -> Graph:
    direct = {n for i in impacts for n in i.direct_claims}
    indirect = {n for i in impacts for n in i.dependency_impacted_claims}
    objected = {n for i in impacts for n in i.objected_claims}
    dispositions = {s.claim_number: s.status for s in statuses}
    nodes = {"OA": GraphNode(id="OA", label="Office Action", kind="office_action")}
    edges = []
    for claim in patent.claims:
        n = claim.claim_number
        status = (
            dispositions[n]
            if dispositions.get(n) in {"allowed", "withdrawn", "canceled"}
            else "canceled"
            if claim.status == "canceled"
            else "direct"
            if n in direct
            else "objected"
            if n in objected or dispositions.get(n) == "objected"
            else "impacted"
            if n in indirect
            else "unaddressed"
        )
        nodes[f"CL{n}"] = GraphNode(
            id=f"CL{n}", label=f"Claim {n}", kind="claim", status=status, claim_number=n
        )
    for claim in patent.claims:
        for parent in claim.depends_on:
            parent_id = f"CL{parent}"
            if parent_id not in nodes:
                nodes[parent_id] = GraphNode(
                    id=parent_id,
                    label=f"Claim {parent} (missing)",
                    kind="claim",
                    status="missing",
                    claim_number=parent,
                )
            edges.append(
                GraphEdge(
                    source=parent_id,
                    target=f"CL{claim.claim_number}",
                    relation="depends_on",
                    evidence=claim.evidence,
                )
            )
    for rejection in rejections:
        rid = rejection.rejection_id
        label = "Objection" if rejection.action_type == "objection" else rejection.statute
        nodes[rid] = GraphNode(
            id=rid, label=f"{rid} · {label}", kind="rejection", status=rejection.action_type
        )
        edges.append(
            GraphEdge(source="OA", target=rid, relation="contains", evidence=rejection.evidence)
        )
        for number in rejection.claims:
            cid = f"CL{number}"
            if cid not in nodes:
                nodes[cid] = GraphNode(
                    id=cid,
                    label=f"Claim {number} (missing)",
                    kind="claim",
                    status="missing",
                    claim_number=number,
                )
            edges.append(
                GraphEdge(
                    source=rid,
                    target=cid,
                    relation="directly_addresses",
                    evidence=rejection.evidence,
                )
            )
        seen_citations = set()
        for ref in rejection.cited_references:
            if ref.citation_id in seen_citations:
                continue
            seen_citations.add(ref.citation_id)
            nodes[ref.citation_id] = GraphNode(
                id=ref.citation_id,
                label=reference_label(ref),
                kind="citation",
                status="relied_upon"
                if nodes.get(ref.citation_id) and nodes[ref.citation_id].status == "relied_upon"
                else ref.citation_role,
            )
            edges.append(
                GraphEdge(
                    source=rid,
                    target=ref.citation_id,
                    relation="cites",
                    evidence=ref.evidence,
                    citation_role=ref.citation_role,
                )
            )
    return Graph(nodes=list(nodes.values()), edges=edges)
