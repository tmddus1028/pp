"""Golden local improvement API checks; refuses to invoke configured cloud providers."""

import json
from pathlib import Path

import httpx

from backend.config import Settings
from backend.improvements.service import provider_settings

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/outputs/improvements"


def main():
    config = Settings()
    if any(
        provider_settings(config, jurisdiction).llm_provider != "local"
        for jurisdiction in ("us", "kr")
    ):
        raise SystemExit(
            "This regression script runs only with local improvement providers; no cloud request sent."
        )
    reports = []
    for pair, number, rid in [
        (1, 1, "R1"),
        (1, 1, "R2"),
        (2, 1, "R1"),
        (3, 15, "R6"),
        (3, 16, "R6"),
        (3, 1, "R1"),
        ("kr", 1, "R1"),
    ]:
        if pair == "kr":
            folder = ROOT / "korean_prototype/data/kr_1020190000844"
            response = httpx.post(
                "http://127.0.0.1:8000/analyze/files?jurisdiction=KR",
                files={
                    "patent": ("KR20190025857A.pdf", (folder / "KR20190025857A.pdf").read_bytes()),
                    "office_action": (
                        "office_action_20190409.xml",
                        (folder / "office_action_20190409.xml").read_bytes(),
                    ),
                },
                timeout=120,
            )
            response.raise_for_status()
            analysis = response.json()
            assert len(analysis["patent"]["claims"]) == 1
            assert analysis["claim_summary"]["direct_rejected_claims"] == [1]
            assert len(analysis["citations"]) == 3
            (OUT / "golden/kr-analysis.json").write_text(
                json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        else:
            analysis = json.loads((OUT / f"golden/pair-{pair}.json").read_text(encoding="utf-8"))
        before = json.dumps(analysis, sort_keys=True)
        response = httpx.post(
            "http://127.0.0.1:8000/improvements",
            json={"analysis": analysis, "claim_number": number, "rejection_id": rid},
            timeout=120,
        )
        assert response.status_code == 200, response.text
        review = response.json()
        assert review["provider"] == "local"
        assert review["claim_number"] == number and review["rejection_id"] == rid
        assert {b["rejection_id"] for b in review["suggestion"]["rejection_basis"]} == {rid}
        source_ids = {s["evidence_id"] for s in review["sources"]}
        for strategy in review["suggestion"]["strategies"]:
            assert set(strategy["evidence_ids"]) <= source_ids
        rewrite = any(
            s["action_type"] == "dependency_rewrite" for s in review["suggestion"]["strategies"]
        )
        assert rewrite == (pair == 3 and number in {15, 16})
        assert json.dumps(analysis, sort_keys=True) == before
        name = f"pair-{pair}-claim-{number}-{rid}"
        (OUT / (name + ".json")).write_text(
            json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        reports.append(
            {
                "case": name,
                "result": "PASS",
                "provider": "local",
                "status": review["status"],
                "dependency_rewrite": rewrite,
                "evidence_count": len(source_ids),
                "missing_evidence": review["suggestion"]["missing_evidence"],
            }
        )
        print(name, "PASS", flush=True)
    (OUT / "improvement-checks.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
