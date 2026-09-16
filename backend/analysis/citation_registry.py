"""One document identity, many role- and source-specific rejection relationships."""

import hashlib
import re

from backend.analysis.bibliography import normalize_doi
from backend.analysis.citation_analyzer import extract_citations, name_key
from backend.ingestion.adapters import evidence_at
from backend.schemas import CitationDocument, RejectionCitation


def normalized(value):
    return re.sub(r"[\W_]+", "", (value or "").casefold())


def canonical_key(ref, kinds=None):
    if ref.publication_number:
        base = re.sub(r"[AB]\d$", "", ref.publication_number)
        # A missing kind joins a single explicit kind, but A1 and A2 remain distinct.
        return "publication:" + (
            ref.publication_number if len((kinds or {}).get(base, set())) > 1 else base
        )
    if ref.doi:
        return "doi:" + normalize_doi(ref.doi)
    author = name_key(ref.name or "")
    if ref.title:
        return "title:" + author + ":" + normalized(ref.title)
    if ref.publication and ref.year:
        return "bibliography:" + ":".join(
            [
                author,
                normalized(ref.publication),
                str(ref.year),
                normalized(
                    ref.bibliographic_locator
                    or (ref.definition_evidence.text if ref.definition_evidence else ref.raw_text)
                ),
            ]
        )
    # Incomplete, ambiguous author-only mentions are not a license to merge papers.
    return f"unresolved:{ref.evidence.document_id}:{ref.evidence.start}:{author}"


def not_relied_references(document):
    refs = []
    for match in re.finditer(r"\bnot\s+relied\s+(?:upon|on)\b", document.text, re.I):
        tail = document.text[match.end() :]
        stop = re.search(
            r"\b(?:Any\s+inquiry|Claims?\s+[\d, -]+\s+(?:is|are)\s+rejected|Conclusion)\b",
            tail,
            re.I,
        )
        end = match.end() + stop.start() if stop else len(document.text)
        evidence = evidence_at(document, match.end(), end)
        for ref in extract_citations(evidence.text, evidence, document):
            if ref.type != "unknown":
                ref.citation_role = "not_relied_upon"
                refs.append(ref)
    return refs


def build_citation_registry(document, rejections):
    occurrences = [(r, ref) for r in rejections for ref in r.cited_references]
    occurrences += [(None, ref) for ref in not_relied_references(document)]
    kinds = {}
    for _, ref in occurrences:
        if ref.publication_number:
            match = re.search(r"[AB]\d$", ref.publication_number)
            if match:
                kinds.setdefault(ref.publication_number[:-2], set()).add(match[0])
    definitions = {}
    for _, ref in occurrences:
        key = canonical_key(ref, kinds)
        if not key.startswith("unresolved:") and ref.name:
            definitions.setdefault(name_key(ref.name), {})[key] = ref
    catalog, edges = {}, []
    for rejection, ref in occurrences:
        key = canonical_key(ref, kinds)
        # Explicit '(Liu)' aliases may resolve only against one bibliography in
        # this OA. A bare name or similar spelling alone is never sufficient.
        candidates = definitions.get(name_key(ref.name or ""), {})
        if key.startswith("unresolved:") and ref.explicit_alias and len(candidates) == 1:
            key, definition = next(iter(candidates.items()))
            for field in (
                "name",
                "publication_number",
                "doi",
                "title",
                "publication",
                "year",
                "bibliographic_locator",
                "type",
            ):
                setattr(ref, field, getattr(definition, field))
            ref.definition_evidence = definition.definition_evidence or definition.evidence
        ref.canonical_key = key
        ref.citation_id = "CIT-" + hashlib.sha256(key.encode()).hexdigest()[:12]
        rid = rejection.rejection_id if rejection else None
        edge = RejectionCitation(
            rejection_id=rid,
            citation_id=ref.citation_id,
            role=ref.citation_role,
            evidence=ref.evidence,
            claim_numbers=rejection.claims if rejection else [],
        )
        # Repeated mentions keep all original source occurrences, without new documents.
        if not any(e == edge for e in edges):
            edges.append(edge)
        if ref.citation_id not in catalog:
            catalog[ref.citation_id] = CitationDocument(
                citation_id=ref.citation_id,
                canonical_key=key,
                display_name=ref.name or ref.publication_number or "인용 문헌",
                authors=[ref.name] if ref.name else [],
                title=ref.title,
                publication_number=ref.publication_number,
                doi=ref.doi,
                journal=ref.publication,
                year=ref.year,
                type=ref.type,
                citation_role=ref.citation_role,
                citation_roles=[ref.citation_role],
                evidence=ref.definition_evidence or ref.evidence,
            )
        item = catalog[ref.citation_id]
        if ref.citation_role not in item.citation_roles:
            item.citation_roles.append(ref.citation_role)
        item.citation_role = min(
            item.citation_roles, key=["relied_upon", "supporting_evidence", "not_relied_upon"].index
        )
    for rejection in rejections:
        unique = {}
        for ref in rejection.cited_references:
            unique.setdefault((ref.citation_id, ref.citation_role), ref)
        rejection.cited_references = list(unique.values())
    return list(catalog.values()), edges
