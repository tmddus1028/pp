"""View model over the existing analysis contract; no new legal inference."""

import re


def relied_references(rejection):
    """User-facing references; all roles remain in the original analysis/model."""
    return [
        ref
        for ref in rejection["cited_references"]
        if ref.get("citation_role", "relied_upon") == "relied_upon"
    ]


def _source(document, start, end):
    return {
        "document_id": document["document_id"],
        "start": start,
        "end": end,
        "text": document["text"][start:end],
        "page_numbers": [
            p["number"] for p in document["pages"] if p["start"] < end and p["end"] > start
        ],
    }


def explicit_support(result):
    """Link only explicit OA paragraph/figure references found in the patent."""
    if result["analysis_id"].startswith("kr-"):
        return [
            {
                "id": f"spec-kr-{i}",
                "label": link["label"],
                "rejection_id": link["rejection_id"],
                "evidence": link["evidence"],
                "figure": None,
                "provenance": link["provenance"],
            }
            for i, link in enumerate(result.get("evidence_links", []))
            if link.get("citation_id") is None
        ]
    patent = next(d for d in result["documents"] if d["kind"] == "patent")
    claim_start = min(c["evidence"]["start"] for c in result["patent"]["claims"])
    text = patent["text"][:claim_start]
    links = []
    for rejection in result["rejections"]:
        oa = rejection["evidence"]["text"]
        requested = {m[1] for m in re.finditer(r"\[(\d{4})\]", oa)}
        for number in sorted(requested):
            matches = list(re.finditer(rf"(?m)^\s*(?:\[{number}\]|\(?{number}[.)]?)\s+", text))
            if len(matches) != 1:
                continue
            match = matches[0]
            end = re.search(r"(?m)^\s*(?:\[\d{4}\]|\(?\d{4}[.)]?)\s+", text[match.end() :])
            stop = min(match.end() + end.start() if end else len(text), match.end() + 2400)
            links.append(
                {
                    "id": f"spec-{rejection['rejection_id']}-{number}",
                    "label": f"Paragraph [{number}]",
                    "rejection_id": rejection["rejection_id"],
                    "evidence": _source(patent, match.start(), stop),
                    "figure": None,
                }
            )
        figures = {
            m[1].upper() for m in re.finditer(r"\bfig(?:ure)?\.?\s*(\d+[A-Za-z]?)\b", oa, re.I)
        }
        for number in sorted(figures):
            # Require a caption line; do not claim an arbitrary prose mention is a drawing.
            matches = list(re.finditer(rf"(?im)^\s*FIG(?:URE)?\.?\s*{number}\s*$", text))
            if len(matches) == 1:
                m = matches[0]
                links.append(
                    {
                        "id": f"figure-{rejection['rejection_id']}-{number}",
                        "label": f"Figure {number}",
                        "rejection_id": rejection["rejection_id"],
                        "evidence": _source(patent, m.start(), m.end()),
                        "figure": number,
                    }
                )
    return links


def build_review_model(result):
    docs = {d["document_id"]: d for d in result["documents"]}
    items, annotations = [], []
    impacts = {i["rejection_id"]: i for i in result["impacts"]}
    rejections = {r["rejection_id"]: r for r in result["rejections"]}
    dispositions = {s["claim_number"]: s for s in result.get("claim_statuses", [])}
    support = explicit_support(result)

    def add_annotations(item, evidence, role, rid=None):
        document = docs[evidence["document_id"]]
        rids = [rid] if rid else item["rejection_ids"]
        statutes = list(dict.fromkeys(rejections[r]["statute"] for r in rids))
        for number in evidence["page_numbers"]:
            page = document["pages"][number - 1]
            start, end = max(evidence["start"], page["start"]), min(evidence["end"], page["end"])
            if start >= end:
                continue
            annotations.append(
                {
                    "id": f"{item['id']}:{role}:{rid or ''}:{number}:{evidence['start']}",
                    "item_id": item["id"],
                    "document_id": document["document_id"],
                    "page": number,
                    "type": role,
                    "claim_number": item.get("claim_number"),
                    "statute": " · ".join(statutes) or None,
                    "evidence_text": document["text"][start:end],
                    "start": start - page["start"],
                    "end": end - page["start"],
                    "linked_rejection_id": rids[0] if len(rids) == 1 else None,
                    "linked_rejection_ids": list(rids),
                    "bbox": None,
                    "boxes": [],
                    "location_method": "unresolved",
                }
            )

    for claim in result["patent"]["claims"]:
        n = claim["claim_number"]
        disposition = dispositions.get(n, {})
        status = disposition.get("status", claim["status"])
        direct = [
            rid
            for rid, impact in impacts.items()
            if n in impact["direct_claims"] and rejections[rid]["action_type"] == "rejection"
        ]
        objected = [
            rid
            for rid, rejection in rejections.items()
            if rejection["action_type"] == "objection" and n in rejection["claims"]
        ]
        indirect = [
            rid for rid, impact in impacts.items() if n in impact["dependency_impacted_claims"]
        ]
        if status in {"allowed", "withdrawn", "canceled"}:
            direct, indirect, objected = [], [], []
        related = list(dict.fromkeys(direct + indirect + objected))
        item = {
            "id": f"claim-{n}",
            "kind": "claim",
            "title": f"Claim {n}",
            "claim_number": n,
            "text": claim["text"],
            "evidence": claim["evidence"],
            "direct": direct,
            "indirect": indirect,
            "objected": objected,
            "rejection_ids": related,
            "depends_on": claim["depends_on"],
            "status": status,
            "status_evidence": disposition.get("evidence"),
            "conditional_allowance": disposition.get("conditional_allowance", False),
            "children": [
                c["claim_number"] for c in result["patent"]["claims"] if n in c["depends_on"]
            ],
            "support_ids": [s["id"] for s in support if s["rejection_id"] in related],
        }
        items.append(item)
        role = (
            "direct_rejection"
            if direct
            else "dependency"
            if indirect or objected
            else "unaddressed"
        )
        add_annotations(item, claim["evidence"], role)
    for rejection in result["rejections"]:
        rid = rejection["rejection_id"]
        item = {
            "id": f"rejection-{rid}",
            "kind": "rejection",
            "title": f"{rid} · "
            + ("Objection" if rejection["action_type"] == "objection" else rejection["statute"]),
            "action_type": rejection["action_type"],
            "evidence": rejection["evidence"],
            "rejection_ids": [rid],
            "text": rejection["reason_summary"],
        }
        items.append(item)
        add_annotations(
            item,
            rejection["evidence"],
            "dependency" if rejection["action_type"] == "objection" else "direct_rejection",
            rid,
        )
        for ref in [] if result.get("citations") else rejection["cited_references"]:
            cid = "citation-" + ref["citation_id"]
            item = next((i for i in items if i["id"] == cid), None)
            if item is None:
                item = {
                    "id": cid,
                    "kind": "citation",
                    "title": ref["name"] or ref["publication_number"] or "인용 문헌",
                    "reference": ref,
                    "evidence": ref["evidence"],
                    "rejection_ids": [],
                    "text": ref.get("raw_text") or ref["evidence"]["text"],
                }
                items.append(item)
            item["rejection_ids"].append(rid)
            add_annotations(item, ref["evidence"], "citation", rid)
    for citation in result.get("citations", []):
        occurrences = [
            edge
            for edge in result.get("rejection_citations", [])
            if edge["citation_id"] == citation["citation_id"]
        ]
        rids = list(
            dict.fromkeys(edge["rejection_id"] for edge in occurrences if edge["rejection_id"])
        )
        reference = {
            **citation,
            "name": citation["display_name"],
            "publication": citation.get("journal"),
        }
        item = {
            "id": "citation-" + citation["citation_id"],
            "kind": "citation",
            "title": citation["display_name"],
            "reference": reference,
            "evidence": citation["evidence"],
            "rejection_ids": rids,
            "text": citation["evidence"]["text"],
            "citation_role": citation["citation_role"],
            "occurrences": occurrences,
            "source_links": [
                link
                for link in result.get("evidence_links", [])
                if link.get("citation_id") == citation["citation_id"]
            ],
            "affected_claims": sorted({n for edge in occurrences for n in edge["claim_numbers"]}),
        }
        items.append(item)
        for link in item["source_links"]:
            add_annotations(item, link["evidence"], "citation", link["rejection_id"])
        for occurrence in occurrences:
            add_annotations(
                item,
                occurrence["evidence"],
                "citation" if occurrence["role"] == "relied_upon" else "specification",
                occurrence["rejection_id"],
            )
    for link in support:
        item = {
            "id": link["id"],
            "kind": "specification",
            "title": link["label"],
            "evidence": link["evidence"],
            "text": link["evidence"]["text"],
            "figure": link["figure"],
            "rejection_ids": [link["rejection_id"]],
        }
        items.append(item)
        add_annotations(item, link["evidence"], "specification", link["rejection_id"])
    return {
        "analysis_id": result["analysis_id"],
        "provider": result["provider"],
        "documents": [
            {
                "id": d["document_id"],
                "filename": d["filename"],
                "kind": d["kind"],
                "pages": d["pages"],
                "ocr_pages": d.get("metadata", {}).get("ocr_pages", []),
            }
            for d in result["documents"]
        ],
        "items": items,
        "annotations": annotations,
        "rejections": list(rejections.values()),
        "impacts": result["impacts"],
        "warnings": result["warnings"],
        "claim_summary": result.get("claim_summary", {}),
    }
