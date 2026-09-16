import hashlib
import re

from backend.ingestion.adapters import evidence_at
from backend.schemas import CitedReference, Document, Evidence

PUBLICATION = re.compile(
    r"\b(?:USPAP|USPN|US|U\.S\.|WO)\s*(?:PG\s+PUB\s+)?(?:(?:Pat(?:ent)?\.?|Pub(?:lication)?\.?)\s*)?"
    r"(?:(?:No|Number)\.?\s*)?(?:\d{4}\s*/\s*\d{6,7}|\d{1,3}(?:,\d{3}){2}|\d{7,11})"
    r"(?:\s*[AB]\s*\d)?\b",
    re.I,
)
NAMED_REFERENCE = re.compile(
    r"(?i:\b(?:over|in view of|anticipated by|disclosed by|taught by|further in view of)\s+)"
    r"(?P<name>[A-Z][A-Za-z'’-]+(?:\s+[A-Z][A-Za-z'’-]+){0,2}(?:\s+et\s+al\.?)?)",
)
AUTHOR = r"[A-Z][A-Za-z'’-]+(?:[ \t]+[A-Z][A-Za-z'’-]+){0,2}"
BEFORE_PUBLICATION = re.compile(rf"(?P<name>{AUTHOR}(?:\s+et\s+al\.?)?)\s*[\[(:,—–-]\s*$")
NPL_AUTHOR = re.compile(rf"\b(?P<name>{AUTHOR}\s+et\s+al\.?)")
YEAR = re.compile(r"\b(?:18|19|20)\d{2}\b")
LOCATOR = re.compile(
    r"[\s),;:]*"
    r"(?:(?:Vol(?:ume)?\.?\s*)?\d{1,4}\s*(?:\(\s*\d+(?:-\d+)?\s*\))?"
    r"(?:\s*:\s*\d+)?\s*,?\s*)?"
    r"(?:(?:pp?|pages)\.?\s*)?\d+\s*[-–]\s*\d+"
    r"|[\s),;:]+(?:Vol(?:ume)?\.?\s*)?\d{1,7}"
    r"(?:\s*\(\s*\d+(?:-\d+)?\s*\))?(?:\s*:\s*\d+)?",
    re.I,
)


def normalize_publication(value: str | None) -> str | None:
    if value is None:
        return None
    match = PUBLICATION.search(value)
    if not match:
        return None
    country = "WO" if match[0][:2].upper() == "WO" else "US"
    tail = re.sub(r"^(?:USPAP|USPN|US|U\.S\.|WO)", "", match[0], flags=re.I)
    tail = re.sub(r"(?i)pg\s+pub|patent|publication|number|pat|pub|no", "", tail)
    return country + re.sub(r"[^0-9AB]", "", tail.upper())


def citation_id(name: str | None, publication: str | None, scope: str = "") -> str:
    key = publication or scope + ":" + re.sub(r"\W+", "", (name or "unknown").casefold())
    return "CIT-" + hashlib.sha256(key.encode()).hexdigest()[:12]


def name_key(value: str) -> str:
    value = re.sub(r",?\s+et\s*al\.?$", "", value.strip(), flags=re.I)
    return re.sub(r"[\W_]+", "", value.casefold())


def reference_label(ref: CitedReference) -> str:
    number = ref.publication_number
    if number:
        number = re.sub(r"^(WO)(\d{4})(\d{6})([AB]\d)?$", r"\1\2/\3 \4", number).strip()
        number = re.sub(r"^(US)(\d{4})(\d{7})([AB]\d)?$", r"\1 \2/\3 \4", number).strip()
    return (
        " · ".join(
            part for part in (ref.name, number or ("NPL" if ref.type == "npl" else None)) if part
        )
        or ref.citation_id
    )


def extract_citations(
    text: str, evidence: Evidence, document: Document | None = None
) -> list[CitedReference]:
    # Only source spans are accepted. Never derive evidence from an LLM summary.
    if text != evidence.text:
        raise ValueError("Citation text must match its source evidence")

    def span(start: int, end: int) -> Evidence:
        if document is not None:
            return evidence_at(document, evidence.start + start, evidence.start + end)
        return evidence.model_copy(
            update={
                "text": text[start:end],
                "start": evidence.start + start,
                "end": evidence.start + end,
            }
        )

    named = list(NAMED_REFERENCE.finditer(text))
    refs: dict[str, CitedReference] = {}
    # Publication-backed names also cover slash-separated combinations such as
    # Scipioni (USPAP ...)/Del Favero et al (USPN ...).
    for match in PUBLICATION.finditer(text):
        publication = normalize_publication(match[0])
        prefix = max(0, match.start() - 150)
        preceding = BEFORE_PUBLICATION.search(text[prefix : match.start()])
        name = re.sub(r"\s+", " ", preceding["name"]).rstrip(".") if preceding else None
        start = prefix + preceding.start("name") if preceding else match.start()
        source = span(start, match.end())
        key = citation_id(name, publication)
        if key not in refs or (name and not refs[key].name):
            refs[key] = CitedReference(
                citation_id=key,
                name=name,
                publication_number=publication,
                evidence=source,
                type="patent",
                raw_text=source.text,
            )

    # A repeated number may omit A1/A2/B2. Resolve only to a single explicit
    # kind for that exact number; different kinds are never merged together.
    for key, ref in list(refs.items()):
        number = ref.publication_number
        if number and not re.search(r"[AB]\d$", number):
            specific = [
                r
                for r in refs.values()
                if r.publication_number != number
                and re.sub(r"[AB]\d$", "", r.publication_number or "") == number
            ]
            if len(specific) == 1:
                del refs[key]

    # NPL needs an author, publication, year AND a bibliographic locator. An
    # author mentioned in ordinary examiner prose alone is not a new paper.
    authors = list(NPL_AUTHOR.finditer(text))
    for index, author in enumerate(authors):
        stop = authors[index + 1].start() if index + 1 < len(authors) else len(text)
        tail = text[author.end() : min(stop, author.end() + 600)]
        year = YEAR.search(tail)
        if not year or PUBLICATION.search(tail[: year.end()]):
            continue
        before_year = re.sub(r"\s+", " ", tail[: year.start()]).strip(' ,;:(—–-"[')
        volume = re.search(r",?\s*vol(?:ume)?\.?\s+(\d+(?:\(\d+\))?)\s*$", before_year, re.I)
        publication = before_year[: volume.start()].rstrip(" ,") if volume else before_year
        if not publication or not publication[0].isupper() or len(publication) > 250:
            continue
        locator = LOCATOR.match(tail, year.end())
        if not locator:
            continue
        name = re.sub(r"\s+", " ", author["name"]).rstrip(".")
        # Exact bibliographic identity, never fuzzy author matching. Different
        # journals, years, volumes/pages or quoted titles keep different nodes.
        identity = "|".join(
            (
                name_key(name),
                re.sub(r"\W+", "", publication.casefold()),
                year[0],
                ":".join(([volume[1]] if volume else []) + re.findall(r"\d+", locator[0])),
            )
        )
        key = "CIT-" + hashlib.sha256(("npl|" + identity).encode()).hexdigest()[:12]
        source = span(author.start("name"), author.end() + locator.end())
        refs.setdefault(
            key,
            CitedReference(
                citation_id=key,
                name=name,
                publication_number=None,
                type="npl",
                publication=publication,
                year=int(year[0]),
                raw_text=source.text,
                evidence=source,
            ),
        )

    numbered_names = {name_key(ref.name) for ref in refs.values() if ref.name}
    for index, match in enumerate(named):
        name = re.sub(r"\s+", " ", match["name"]).strip().rstrip(".")
        if name.lower() in {"the", "a", "an", "claims", "claim", "us", "u"}:
            continue
        stop = named[index + 1].start() if index + 1 < len(named) else len(text)
        following = text[match.end() : min(stop, match.end() + 130)]
        # Attach only an immediately parenthesized publication, never a distant reference.
        pub = PUBLICATION.search(following) if re.match(r"\s*\(", following) else None
        publication = normalize_publication(pub[0]) if pub else None
        if publication or name_key(name) in numbered_names:
            continue
        key = citation_id(name, publication, f"{evidence.document_id}:{evidence.start}")
        refs[key] = CitedReference(
            citation_id=key,
            name=name,
            publication_number=publication,
            evidence=span(match.start("name"), match.end("name")),
            raw_text=text[match.start("name") : match.end("name")],
        )
    # Parenthesized bibliography and explicit aliases have tighter boundaries
    # than the legacy free-form NPL pattern. Do not borrow the next author's title.
    from backend.analysis.bibliography import parenthetical_references

    rich = parenthetical_references(text, evidence)
    for ref in rich:
        ref.evidence = span(ref.evidence.start - evidence.start, ref.evidence.end - evidence.start)
    values = [
        r
        for r in refs.values()
        if not any(
            r.evidence.start < other.evidence.end and other.evidence.start < r.evidence.end
            for other in rich
        )
    ] + rich
    for ref in values:
        number = ref.publication_number
        if number and not re.search(r"[AB]\d$", number):
            specific = {
                r.publication_number
                for r in values
                if r.publication_number
                and r.publication_number != number
                and re.sub(r"[AB]\d$", "", r.publication_number) == number
            }
            if len(specific) == 1:
                ref.publication_number = next(iter(specific))
                ref.citation_id = citation_id(ref.name, ref.publication_number)
    return sorted(values, key=lambda ref: ref.evidence.start)


def extract_relied_citations(evidence: Evidence, document: Document) -> list[CitedReference]:
    """Keep an explicit reliance clause and its bibliography, not every PDF number."""
    text = evidence.text
    cutoff = re.search(r"\b(?:not\s+relied\s+(?:upon|on)|for\s+background\s+only)\b", text, re.I)
    refs = extract_citations(text, evidence, document)
    kept = []
    previous_end = 0
    previous_kept = False
    for ref in refs:
        start, end = ref.evidence.start - evidence.start, ref.evidence.end - evidence.start
        if cutoff and start > cutoff.start():
            continue
        gap = re.sub(r"\s+", " ", text[previous_end:start]).strip()
        reliance = re.search(
            r"\b(?:over|in (?:further )?view of|anticipated by|disclosed by|taught by|as evidenced by|"
            r"relied (?:upon|on)|based on)(?:\s+[^.!?]*)?$",
            gap,
            re.I,
        )
        continuation = previous_kept and re.fullmatch(
            r"[\s,;:.)\]/\-–—]*(?:(?:and|or)\s*)?", gap, re.I
        )
        following = re.match(r"[\s).,]*is\s+(?:presented|cited)\s+as\s+evidence", text[end:], re.I)
        previous_kept = bool(reliance or continuation or following)
        if previous_kept:
            if following or re.search(r"\bas\s+evidenced\s+by\s*$", gap, re.I):
                ref.citation_role = "supporting_evidence"
            kept.append(ref)
        previous_end = end
    return kept
