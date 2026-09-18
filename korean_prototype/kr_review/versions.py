"""Date-ordered supplied claim history with conservative, explicit uncertainty."""

import hashlib
from datetime import date

from .models import ReviewError


def select_version(original, amendments, history, oa_date):
    default = {
        "status": "uncertain",
        "reason": "심사 당시 청구범위 및 보정 이력의 확인 자료가 없습니다.",
    }
    if not history:
        if amendments:
            raise ReviewError(
                "보정 청구범위 파일에는 제출일·파일 SHA-256을 포함한 version_history가 필요합니다."
            )
        return original, default
    try:
        cutoff = date.fromisoformat(oa_date)
        files = {
            hashlib.sha256(data).hexdigest(): (data, name) for data, name in [original, *amendments]
        }
        events = []
        for record in history.get("submissions", []):
            submitted = date.fromisoformat(record["submitted_at"])
            digest = record["sha256"]
            if digest not in files:
                raise ReviewError("청구범위 이력의 해시와 제공 파일이 일치하지 않습니다.")
            if submitted <= cutoff:
                events.append((submitted, digest))
    except (KeyError, TypeError, ValueError) as exc:
        raise ReviewError("청구범위 이력 또는 의견제출통지서 날짜를 확인할 수 없습니다.") from exc
    if not events:
        return original, {
            **default,
            "reason": "OA 이전 제출 청구범위를 제공 이력에서 확인하지 못했습니다.",
        }
    events.sort()
    if len({digest for d, digest in events if d == events[-1][0]}) > 1:
        raise ReviewError("같은 제출일의 청구범위 버전이 여러 개여서 선택할 수 없습니다.")
    candidate = events[-1][1]
    # Dates alone do not prove filing history completeness. Only an explicit
    # caller selection activates the candidate; preserve this provenance.
    selected = history.get("selected_sha256")
    if selected and selected != candidate:
        raise ReviewError("선택 청구범위가 제공된 OA 이전 최종 제출 이력과 다릅니다.")
    info = {
        "status": "uncertain",
        "candidate_sha256": candidate,
        "submitted_at": events[-1][0].isoformat(),
        "office_action_date": oa_date,
        "selection_source": "user_supplied_history" if selected else "date_candidate_only",
        "reason": "제공 이력에서 OA 이전 후보를 찾았습니다. 이력 완전성과 실제 심사 적용 여부는 원문 확인이 필요합니다.",
    }
    return files[selected] if selected else original, info
