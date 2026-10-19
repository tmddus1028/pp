"""Common rejection types shared by KR (특허법) and US (35 U.S.C.) rejections.

Mapping draft from the redesign doc (2026-10-19). Re-check article numbers against the statute
text before relying on them. Only novelty/inventive_step reuse US response cases fully.
"""

import re

CATEGORIES = {
    "novelty": {"label": "신규성", "kr": "제29조제1항", "us": "35 U.S.C. 102", "reuse": "high"},
    "inventive_step": {
        "label": "진보성",
        "kr": "제29조제2항",
        "us": "35 U.S.C. 103",
        "reuse": "high",
    },
    "description": {
        "label": "기재불비",
        "kr": "제42조제3항·제4항",
        "us": "35 U.S.C. 112(a)·(b)",
        "reuse": "partial",
    },
    "eligibility": {
        "label": "발명 성립성·산업상 이용가능성",
        "kr": "제29조제1항 본문",
        "us": "35 U.S.C. 101",
        "reuse": "low",
    },
    "prior_application": {
        "label": "선출원·확대된 선출원·이중특허",
        "kr": "제36조, 제29조제3항",
        "us": "35 U.S.C. 102(a)(2), double patenting",
        "reuse": "low",
    },
    "other": {"label": "기타", "kr": "", "us": "", "reuse": "low"},
}

REUSABLE = {"novelty", "inventive_step", "description"}


def _compact(text):
    return re.sub(r"\s+", "", text or "")


def categorize(statute, jurisdiction=None, text=""):
    """Map a raw statute string (KR or US) to a common category key."""
    raw = statute or ""
    s = _compact(raw)
    us = jurisdiction in {"us", "US"} or bool(re.search(r"U\.?S\.?C|§|USC", raw))
    if not us:
        if re.search(r"제?29조(?:의)?제?3항|제?36조|29조의2", s):
            return "prior_application"
        if re.search(r"제?29조제?2항", s):
            return "inventive_step"
        if re.search(r"제?29조제?1항(?:제?\d+호)", s):
            return "novelty"
        if re.search(r"제?29조제?1항본문", s):
            return "eligibility"
        if re.search(r"제?29조제?1항", s):
            # 본문(산업상 이용가능성) vs 각 호(신규성): tell them apart by the reasoning text.
            if re.search(r"산업상\s*이용|발명에\s*해당하지|자연법칙", text or ""):
                return "eligibility"
            return "novelty"
        if re.search(r"제?42조제?[34]항", s):
            return "description"
        if re.search(r"제?2조제?1호|제?32조", s):
            return "eligibility"
    if re.search(r"double\s*patenting", raw, re.I):
        return "prior_application"
    number = re.search(r"(?<!\d)(101|102|103|112)(?!\d)", raw)
    if number:
        return {
            "101": "eligibility",
            "102": "novelty",
            "103": "inventive_step",
            "112": "description",
        }[number.group(1)]
    return "other"


# PatRe "meta.rejection_types" labels, e.g. "103 - Obviousness".
def categorize_patre(label):
    return categorize(label, "us")


def label(category):
    return CATEGORIES.get(category, CATEGORIES["other"])["label"]


# Applicant argument patterns (US REMARKS). Korean labels match the 의견서 vocabulary.
ARGUMENT_TYPES = {
    "element_missing": (
        "인용발명에 청구항 구성이 없다는 주장",
        r"fail(?:s|ed)?\s+to\s+(?:teach|disclose|suggest|show)|does\s+not\s+(?:teach|disclose|"
        r"suggest|show)|do\s+not\s+(?:teach|disclose)|silent\s+(?:as\s+to|regarding)|"
        r"nowhere\s+(?:in|does)",
    ),
    "no_motivation": (
        "결합 동기 부재·사후적 고찰 주장",
        r"motivation|reason\s+to\s+combine|hindsight|improper(?:ly)?\s+combin|"
        r"would\s+not\s+have\s+(?:been\s+)?(?:obvious|combined)|render\s+.{0,40}inoperable|"
        r"change\s+the\s+principle\s+of\s+operation",
    ),
    "teach_away": ("인용발명이 반대로 교시한다는 주장", r"teach(?:es|ing)?\s+away"),
    "unexpected_effect": (
        "예측하지 못한 현저한 효과 주장",
        r"unexpected(?:ly)?\s+(?:result|effect|benefit|advantage|superior)|synergis",
    ),
    "limitation_added": (
        "청구항에 한정을 추가하는 보정",
        r"amended\s+to\s+(?:recite|include|require|specify|further|now)|"
        r"(?:now|as\s+amended,?\s+(?:claim\s+\d+\s+)?)recites?|added\s+(?:the\s+)?limitation|"
        r"amend(?:s|ed|ing)?\s+(?:independent\s+)?claims?\s+\d+(?:\s*(?:,|and)\s*\d+)*\s+(?:by|to)\b",
    ),
    "dependent_merge": (
        "종속항 구성을 독립항에 병합",
        r"incorporat\w*\s+(?:the\s+)?(?:limitations?|subject\s+matter|features?|elements?)\s+"
        r"(?:of|from|recited\s+in)\s+(?:\w+\s+){0,3}claims?\s+\d|rewritten\s+in\s+independent\s+form|"
        r"incorporat\w*\s+(?:the\s+)?(?:previous|original|dependent|former|canceled)\s+claims?\s+\d",
    ),
    "clarification": (
        "불명확한 용어·선행기재 정정",
        r"amended\s+to\s+clarify|antecedent\s+basis|indefinite|clarif(?:y|ies|ied)",
    ),
    "support_cited": (
        "명세서 뒷받침 위치 제시",
        r"support(?:ed)?\s+(?:for\s+(?:the|this|these)\s+amendments?\s+)?(?:is\s+|can\s+be\s+)?"
        r"(?:found\s+)?(?:at|in|by)\s+.{0,60}(?:\[\d{3,5}\]|paragraph|FIG)",
    ),
}


def argument_types(text):
    return [
        key for key, (_, pattern) in ARGUMENT_TYPES.items() if re.search(pattern, text or "", re.I)
    ]


def argument_label(key):
    return ARGUMENT_TYPES[key][0] if key in ARGUMENT_TYPES else key
