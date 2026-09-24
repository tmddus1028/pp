"""Display view models over the analysis contract; no new legal inference."""

import re

from backend.view.review_model import build_review_model, relied_references

STATUS_LABELS = {
    "objected": "Objection · 추가 검토",
    "allowed": "허용",
    "withdrawn": "심사 대상 제외",
    "canceled": "취소됨",
    "pending": "계류 중",
    "unknown": "추출된 지적 없음",
}


def claim_rows(result):
    model = build_review_model(result)
    rows = []
    for item in model["items"]:
        if item["kind"] != "claim":
            continue
        role, label = (
            ("direct_rejection", "직접 지적")
            if item["direct"]
            else ("dependency", "Objection · 추가 검토")
            if item["objected"] or item["status"] == "objected"
            else ("dependency", "추가 검토 · 종속 영향")
            if item["indirect"]
            else ("unaddressed", STATUS_LABELS.get(item["status"], "추출된 지적 없음"))
        )
        # Match the PDF's direct-first status. Other dependency grounds remain in details.
        primary = item["direct"] or item["objected"] or item["indirect"]
        rejections = [r for r in model["rejections"] if r["rejection_id"] in item["rejection_ids"]]
        statutes = list(
            dict.fromkeys(
                r["statute"]
                for r in rejections
                if r["rejection_id"] in primary and r["statute"] != "unknown"
            )
        )
        rows.append(
            {**item, "role": role, "label": label, "statutes": statutes, "rejections": rejections}
        )
    return sorted(rows, key=lambda row: row["claim_number"]), model


def filter_claims(rows, selected_filter, query):
    query = query.strip()
    if query and (len(query) > 5 or not re.fullmatch(r"[0-9]+", query)):
        return []
    return [
        row
        for row in rows
        if (not query or row["claim_number"] == int(query))
        and (
            selected_filter == "전체"
            or (selected_filter == "직접 지적" and row["role"] == "direct_rejection")
            or (selected_filter == "추가 검토" and row["role"] == "dependency")
            or (selected_filter == "허용" and row["status"] == "allowed")
            or (
                selected_filter in ("§112", "§103")
                and any(
                    re.search(rf"\b{selected_filter[1:]}\b", statute) for statute in row["statutes"]
                )
            )
        )
    ]


def display_statute(statute):
    return re.sub(r"\b35\s+U\.?S\.?C\.?", "35 U.S.C.", statute, flags=re.I)


def comparison_for_claim(model, number, scope="all"):
    claim = next(i for i in model["items"] if i.get("claim_number") == number)
    rejections = [
        r
        for r in model["rejections"]
        if r["rejection_id"] in claim["rejection_ids"]
        and (scope == "all" or r["rejection_id"] == scope)
    ]
    rids = {r["rejection_id"] for r in rejections}
    direct, indirect = rids.intersection(claim["direct"]), rids.intersection(claim["indirect"])
    role, status = (
        ("direct_rejection", "직접 지적")
        if direct
        else ("dependency", "Objection · 추가 검토")
        if claim.get("objected") or claim["status"] == "objected"
        else ("dependency", "종속 영향")
        if indirect
        else ("unaddressed", STATUS_LABELS.get(claim["status"], "추출된 지적 없음"))
    )
    references = {}
    for rejection in rejections:
        for ref in relied_references(rejection):
            entry = references.setdefault(
                ref["citation_id"],
                {
                    "reference": ref,
                    "rejection_ids": [],
                    "claim_numbers": set(),
                    "occurrences": [],
                },
            )
            rid = rejection["rejection_id"]
            if rid not in entry["rejection_ids"]:
                entry["rejection_ids"].append(rid)
                entry["occurrences"].append({"rejection_id": rid, "evidence": ref["evidence"]})
            entry["claim_numbers"].update(rejection["claims"])
    for entry in references.values():
        entry["claim_numbers"] = sorted(entry["claim_numbers"])
    support = [
        i
        for i in model["items"]
        if i["id"] in claim["support_ids"] and rids.intersection(i["rejection_ids"])
    ]
    return {
        "claim": claim,
        "role": role,
        "status": status,
        "rejections": rejections,
        "citations": list(references.values()),
        "support": support,
        "statutes": list(dict.fromkeys(r["statute"] for r in rejections)),
    }


def build_relationship_model(result):
    review = build_review_model(result)
    items = {item["id"]: item for item in review["items"]}
    nodes = []
    for node in result["graph"]["nodes"]:
        item_id = {
            "claim": f"claim-{node.get('claim_number')}",
            "citation": f"citation-{node['id']}",
            "rejection": f"rejection-{node['id']}",
        }.get(node["kind"])
        nodes.append({**node, "item_id": item_id if item_id in items else None})
    return {
        "analysis_id": result["analysis_id"],
        "nodes": nodes,
        "edges": [
            {key: edge.get(key) for key in ("source", "target", "relation", "citation_role")}
            for edge in result["graph"]["edges"]
        ],
        "items": list(items.values()),
        "rejections": review["rejections"],
        "impacts": review["impacts"],
        "documents": [{"filename": d["filename"], "kind": d["kind"]} for d in review["documents"]],
    }
