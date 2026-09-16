"""Explicit examiner dispositions, separate from the patent's claim-list status."""

import re

from backend.ingestion.adapters import evidence_at
from backend.patent.dependency_parser import NUMBER_LIST, parse_number_list
from backend.schemas import ClaimDisposition, ClaimSummary

STATUS_STATEMENT = re.compile(
    r"\bclaims?(?:\(s\))?\s+(?P<numbers>" + NUMBER_LIST + r")\s*,?\s*"
    r"(?:is\s*/\s*are|is|are|remain|remains|have\s+been|has\s+been)\s+"
    r"(?:(?:now|hereby|currently)\s+)?"
    r"(?P<status>rejected|objected\s+to|allowed|withdrawn|cancelled|canceled|pending)\b",
    re.I,
)
TERMINAL = {"allowed", "withdrawn", "canceled"}


def extract_claim_statuses(document, patent, rejections):
    records = {
        c.claim_number: ClaimDisposition(
            claim_number=c.claim_number,
            status="canceled" if c.status == "canceled" else "unknown",
            evidence=c.evidence if c.status == "canceled" else None,
        )
        for c in patent.claims
    }
    events = []
    for match in STATUS_STATEMENT.finditer(document.text):
        status = re.sub(r"\s+", " ", match["status"].lower())
        status = {"cancelled": "canceled", "objected to": "objected"}.get(status, status)
        if status == "rejected":
            continue  # Current rejection blocks below have already checked context/withdrawal.
        # Include the conditional-allowance wording, but never promote it to allowed.
        stop = re.search(r"\.(?=\s|$)", document.text[match.end() :])
        end = match.end() + stop.end() if stop else match.end()
        evidence = evidence_at(document, match.start(), end)
        for number in parse_number_list(match["numbers"]):
            events.append((match.start(), number, status, evidence))
    # Action predicates also support "stand rejected" and bare "Claims ... rejected".
    for rejection in rejections:
        for number in rejection.claims:
            events.append(
                (
                    rejection.evidence.start,
                    number,
                    "rejected" if rejection.action_type == "rejection" else "objected",
                    rejection.evidence,
                )
            )
    for _, number, status, evidence in sorted(events, key=lambda event: event[0]):
        previous = records.get(number)
        if status == "pending" and previous and previous.status not in {"pending", "unknown"}:
            continue  # Pending describes pendency, not a reversal of a substantive disposition.
        records[number] = ClaimDisposition(
            claim_number=number,
            status=status,
            evidence=evidence,
            conditional_allowance=status == "objected"
            and bool(re.search(r"would\s+be\s+allowable\s+if\s+rewritten", evidence.text, re.I)),
        )
    return sorted(records.values(), key=lambda record: record.claim_number)


def summarize_claim_statuses(statuses, impacts):
    summary = ClaimSummary(
        direct_rejected_claims=sorted({n for impact in impacts for n in impact.direct_claims}),
        dependency_impacted_claims=sorted(
            {n for impact in impacts for n in impact.dependency_impacted_claims}
            - {n for impact in impacts for n in impact.direct_claims}
        ),
    )
    for status in ("objected", "allowed", "withdrawn", "canceled", "pending", "unknown"):
        setattr(
            summary, status + "_claims", [r.claim_number for r in statuses if r.status == status]
        )
    return summary
