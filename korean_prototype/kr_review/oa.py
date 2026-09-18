"""Korean OA semantics; only explicit examiner grounds create rejections.

XML row/P variants and PDF sections share this parser. All locators continue to
index the extracted source; canonical labels never replace evidence text.
"""

import re

from .ingestion import evidence_at
from .models import Citation, Rejection, ReviewError

LAW = re.compile(
    r"(?:특허법\s*)?제?\s*(\d+)\s*조(?:\s*의\s*(\d+))?(?:\s*제?\s*(\d+)\s*항)?(?:\s*제?\s*(\d+)\s*호)?"
)
INTRO = re.compile(r"(?m)^\s*(?:\d+[.．]\s*)?이\s*출원(?:은|의)\s*")
REF = re.compile(
    r"(?:인용\s*(?:발명|문헌)|선행\s*기술\s*문헌|비교\s*대상\s*발명)\s*(?:제\s*)?(\d*)\s*[:：]\s*"
)
CLAIM_LIST = re.compile(
    r"(?:청구항\s*)?(?:제\s*)?\d+\s*항?(?:\s*(?:내지|부터|또는|및|,|~|∼|～|[-–—])\s*(?:청구항\s*)?제?\s*\d+\s*항?)*"
)


def statute(value):
    m = LAW.search(value)
    if not m:
        raise ReviewError("법조항을 확인할 수 없습니다.")
    article, sub, paragraph, item = m.groups()
    display = f"특허법 제{article}조" + (f"의{sub}" if sub else "")
    display += f"제{paragraph}항" if paragraph else ""
    display += f"제{item}호" if item else ""
    code = "KR_PATENT_ACT_" + article + ("SUB" + sub if sub else "")
    code += "_" + paragraph if paragraph else ""
    code += "_" + item if item else ""
    return display, code, m[0].strip()


def canonical_publication(text):
    compact = re.sub(r"\s+", "", text).upper().replace("－", "-")
    m = re.search(r"(?:KR)?(?:10-)?((?:19|20)\d{2})-?(\d{7})([AB]\d?)?", compact)
    if m:
        return f"KR{m[1]}{m[2]}{m[3] or 'A'}"
    m = re.search(r"10-(\d{7})", compact)
    if m:
        return "KR10" + m[1]
    m = re.search(r"(?:特開|특개)(?:평|平|HEI|H)(\d{1,2})-(\d{5,6})", compact)
    if m:
        return f"JPH{int(m[1])}{int(m[2])}A"
    m = re.search(r"(?:特開|특개|JP)(\d{4})-?(\d{6})([AB]\d?)?", compact)
    if m:
        return f"JP{m[1]}{m[2]}{m[3] or 'A'}"
    m = re.search(r"\b(TW|US|EP|WO|CN)[-/]?(\d{4})[-/]?(\d{4,9})([AB]\d?)?", compact)
    if m:
        return "".join(x or "" for x in m.groups())
    return ""


def _numbers(value):
    from .parsers import claim_numbers

    m = CLAIM_LIST.search(value)
    return claim_numbers(m[0]) if m else []


def _scope(value, all_claims):
    if "발명의 설명" in value and "청구항" not in value:
        return []
    if re.search(r"(?:청구항\s*)?전항", value):
        explicit = re.search(r"전항\s*\(\s*청구항\s*([^)]*)", value)
        numbers = _numbers(explicit[1]) if explicit else all_claims
        if not numbers:
            raise ReviewError("전항의 심사 대상 청구항 범위를 확인할 수 없습니다.")
        return numbers
    claim = re.search(r"청구항\s*", value)
    return _numbers(value[claim.end() :] if claim else value)


def _regions(document):
    elements = document.metadata.get("xml_elements", [])
    details = [e for e in elements if e["name"] == "RejectionLawDetail"]
    if details:
        return [(e["start"], e["end"], e["path"]) for e in details]
    heading = re.search(r"[\[【]\s*구\s*체\s*적\s*인\s*거\s*절\s*이\s*유\s*[\]】]", document.text)
    if not heading:
        raise ReviewError("구체적인 거절이유 구간을 확인하지 못했습니다.")
    tail = re.search(r"\[\s*첨\s*부\s*\]|<<\s*안\s*내", document.text[heading.end() :])
    end = heading.end() + tail.start() if tail else len(document.text)
    return [(heading.end(), end, None)]


def _rows(document):
    elements = document.metadata.get("xml_elements", [])
    tables = [e for e in elements if e["name"] == "ExaminationLawArticle"]
    if tables:
        table = "\n".join(document.text[e["start"] : e["end"]] for e in tables)
    else:
        start = re.search(r"거절이유가\s*있는\s*부분과\s*관련\s*법조항", document.text)
        stop = re.search(r"구\s*체\s*적\s*인\s*거\s*절\s*이\s*유", document.text)
        if not start or not stop:
            raise ReviewError("거절이유 표를 확인하지 못했습니다.")
        table = document.text[start.end() : stop.start()]
    rows = []
    previous = 0
    for law in LAW.finditer(table):
        prefix = table[previous : law.start()]
        subject = re.search(r"청구항|발명의\s*설명|제\s*\d+\s*항", prefix)
        if subject:
            rows.append((prefix[subject.start() :].strip(), statute(law[0])))
        previous = law.end()
    return rows


def extract_office_action(document):
    text = document.text
    examined = re.search(r"심사\s*대상\s*청구항\s*[:：]\s*([^□\n]+)", text)
    if not examined:
        examined = re.search(r"심사\s*대상\s*청구항\s*[:：]\s*\n+\s*([^□\n]+)", text)
    all_claims = _numbers(examined[1]) if examined else []
    rows = _rows(document)
    blocks = []
    for start, end, path in _regions(document):
        starts = [start + m.start() for m in INTRO.finditer(text[start:end])]
        if not starts:
            starts = [start]
        for i, offset in enumerate(starts):
            stop = starts[i + 1] if i + 1 < len(starts) else end
            body = text[offset:stop]
            # Statutes elsewhere in reasoning do not create new grounds.
            sentence_end = body.find("없습니다")
            intro = body[: sentence_end + 4] if sentence_end >= 0 else body[:500]
            laws = {statute(m[0])[1] for m in LAW.finditer(intro)}
            blocks.append((offset, stop, path, intro, laws))
    if not rows:
        # OCR tables may be unreadable while the examiner's full rejection
        # sentence is intact. Require both an express rejection and one law.
        for _, _, _, intro, laws in blocks:
            if len(laws) == 1 and re.search(r"특허를\s*받을\s*수\s*없습니다", intro):
                law = LAW.search(intro)
                rows.append((intro[: law.start()], statute(law[0])))
        if not rows:
            raise ReviewError("지원하는 형식의 명시적 거절이유를 찾지 못했습니다.")
        document.metadata.setdefault("warnings", []).append(
            "거절이유 표 대신 명시적 거절 문장에서 대상과 법조항을 추출했습니다."
        )
    rejections, citations, registry, used = [], [], {}, set()
    for subject, (display, code, raw) in rows:
        numbers = _scope(subject, all_claims)
        matches = [b for b in blocks if code in b[4]]
        if len(matches) > 1:
            matches = [b for b in matches if _scope(b[3], all_claims) == numbers]
        if len(matches) != 1:
            if len(blocks) == 1 and len(rows) > 1:
                raise ReviewError(
                    "하나의 거절이유 본문에 여러 법조항이 혼재하여 구분할 수 없습니다."
                )
            raise ReviewError(f"{display} 거절이유 표와 본문 구간을 하나로 연결할 수 없습니다.")
        start, end, path, intro, _ = matches[0]
        if start in used:
            raise ReviewError("하나의 거절이유 본문에 여러 청구항 범위 또는 법조항이 연결됩니다.")
        used.add(start)
        if _scope(intro, all_claims) != numbers:
            raise ReviewError("거절이유 표와 본문의 대상 청구항이 일치하지 않습니다.")
        body = text[start:end]
        ids = []
        definitions = list(REF.finditer(body))
        for i, match in enumerate(definitions):
            stop = body.find("\n", match.end())
            if stop < 0:
                stop = len(body)
            # NPL titles may wrap over several lines. Stop at next paragraph.
            snippet = body[match.end() : stop]
            publication = canonical_publication(snippet)
            if not publication and re.search(r"[A-Za-z]{3}", snippet):
                paragraph_end = body.find("\n\n", match.end())
                stop = min(paragraph_end if paragraph_end >= 0 else stop, match.end() + 800)
                snippet = body[match.end() : stop]
                bibliography = re.split(r"에\s*게재", snippet)[0]
                key = "npl:" + re.sub(r"[^a-z0-9]", "", bibliography.lower())
                kind = "npl"
            elif publication:
                key, kind = "patent:" + publication, "patent"
            else:
                key, kind = "unknown:" + re.sub(r"\s+", "", snippet), "unknown"
            if key not in registry:
                citation = Citation(
                    citation_id=f"C{len(citations) + 1}",
                    publication_number=publication,
                    canonical_key=key,
                    type=kind,
                    title=snippet.strip(),
                    aliases=[match[1]] if match[1] else [],
                    confidence="high" if kind != "unknown" else "low",
                    evidence=evidence_at(document, start + match.start(), start + stop, path),
                )
                registry[key] = citation
                citations.append(citation)
            elif match[1] and match[1] not in registry[key].aliases:
                registry[key].aliases.append(match[1])
            ids.append(registry[key].citation_id)
        # Explicit incorporation of an earlier numbered reason, not an
        # indiscriminate union of every reference mentioned in the OA.
        if not ids:
            previous_ground = re.search(r"(?:상기|위)\s*거절이유\s*[‘'\"]?(\d+)", body)
            if previous_ground and 0 < int(previous_ground[1]) <= len(rejections):
                ids = list(rejections[int(previous_ground[1]) - 1].citation_ids)
        rejections.append(
            Rejection(
                rejection_id=f"R{len(rejections) + 1}",
                claims=numbers,
                statute=display,
                statute_code=code,
                raw_statute_text=raw,
                subject="claims" if numbers else "description",
                explanation=body.strip(),
                evidence=evidence_at(document, start, end, path),
                citation_ids=list(dict.fromkeys(ids)),
            )
        )
    return rejections, citations
