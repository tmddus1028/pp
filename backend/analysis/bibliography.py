"""Bibliography parsing on a whitespace view with exact original source offsets."""

import re

from backend.analysis.citation_analyzer import AUTHOR, citation_id, name_key, normalize_publication
from backend.schemas import CitedReference

PAREN_AUTHOR = re.compile(rf"\b(?P<name>{AUTHOR}(?:(?i:,?\s+et\s*al\.?))?)\s*\(")
DOI = re.compile(r"\b10\.\d{4,9}/[^\s<>]+", re.I)
PAGE_HEADER = re.compile(
    r"Application/Control\s+Number:\s*[\d/,]+\s+Page\s+\d+\s+Art\s+Unit:\s*\d+", re.I
)


def whitespace_view(text):
    chars, positions = [], []
    for match in re.finditer(r"\S+", text):
        if chars:
            chars.append(" ")
            positions.append(match.start() - 1)
        chars.extend(match[0])
        positions.extend(range(match.start(), match.end()))
    return "".join(chars), positions


def normalize_doi(value):
    match = DOI.search(value or "")
    if not match:
        return None
    result = match[0].rstrip(".,;").casefold()
    while result.endswith(")") and result.count(")") > result.count("("):
        result = result[:-1]
    return result


def parenthetical_references(text, evidence):
    flat, positions = whitespace_view(text)
    refs = []
    skip_until = 0
    for author in PAREN_AUTHOR.finditer(flat):
        if author.start() < skip_until:
            continue
        opening, depth, closing = author.end() - 1, 1, None
        for index in range(opening + 1, min(len(flat), opening + 1800)):
            depth += (flat[index] == "(") - (flat[index] == ")")
            if not depth:
                closing = index
                break
        if closing is None:
            continue
        name = author["name"].rstrip(".")
        content = PAGE_HEADER.sub("", flat[opening + 1 : closing])
        content = re.sub(r"\s+", " ", content).strip()
        publication = normalize_publication(content)
        doi = normalize_doi(content)
        year = re.search(r"\b(?:18|19|20)\d{2}\b", content)
        alias = name_key(content) == name_key(name)
        if not publication and not doi and not alias and not (year and len(content) > 35):
            continue
        start, end = positions[author.start()], positions[closing] + 1
        source = evidence.model_copy(
            update={
                "start": evidence.start + start,
                "end": evidence.start + end,
                "text": text[start:end],
            }
        )
        title = journal = locator = None
        if year and not publication:
            before = content[: year.start()].rstrip(" ,(")
            # Last comma-delimited capitalized field is the journal, after any title commas.
            journal_start = list(re.finditer(r",\s*(?=[A-Z][a-zA-Z.])", before))
            if journal_start:
                mark = journal_start[-1]
                title = before[: mark.start()].strip(" ,")
                journal = re.sub(r"[, ]+\d.*$", "", before[mark.end() :]).strip()
            else:
                title = before
            locator = content[year.end() :].split(";")[0].strip(" ,)")
        refs.append(
            CitedReference(
                citation_id=citation_id(
                    name, publication, f"{evidence.document_id}:{source.start}"
                ),
                name=name,
                publication_number=publication,
                doi=doi,
                type="patent" if publication else "unknown" if alias else "npl",
                title=title,
                publication=journal,
                year=int(year[0]) if year and not publication else None,
                bibliographic_locator=locator,
                evidence=source,
                raw_text=source.text,
                explicit_alias=alias,
            )
        )
        skip_until = closing + 1
    return refs
