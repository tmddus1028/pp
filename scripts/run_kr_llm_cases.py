"""Run the AI improvement on the 5 official KR cases and record every result.

uv run python scripts/run_kr_llm_cases.py --label qwen3-14b-local
LOCAL_LLM_BASE_URL=http://127.0.0.1:11435 LOCAL_LLM_MODEL=qwen3:32b \\
  uv run python scripts/run_kr_llm_cases.py --label qwen3-32b-s165

Uses the current .env provider (IMPROVEMENT_PROVIDER / LOCAL_LLM_* / ANTHROPIC_*).
Writes data/outputs/llm_runs/<label>/<application>.json and summary.json.
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.config import Settings  # noqa: E402
from backend.errors import ProviderError  # noqa: E402
from backend.improvements.models import ImprovementRequest  # noqa: E402
from backend.improvements.service import generate_improvement  # noqa: E402
from backend.jurisdictions.korean import analyze_korean  # noqa: E402

PACKAGE = ROOT / "data/downloads/kr_review_package"
CASES = {
    "1020190000844": "KR20190025857A",
    "1020190000874": "KR20190003855A",
    "1020190000902": "KR20190004821A",
    "1020190000903": "KR20190019097A",
    "1020190000948": "KR20190005244A",
}


def inputs(app):
    folder = next((PACKAGE / "official_samples").glob(f"{app}_*"))
    oa = folder / f"{folder.name}.xml"
    patent = PACKAGE / "publications" / f"{CASES[app]}.pdf"
    return patent, oa


def run(app, settings):
    patent, oa = inputs(app)
    result = analyze_korean(
        patent.read_bytes(), patent.name, oa.read_bytes(), oa.name, settings.max_document_chars
    )
    claims = sorted(
        {n for r in result.rejections if r.action_type == "rejection" for n in r.claims}
    )
    started = time.time()
    record = {"application": app, "claim_number": claims[0] if claims else None}
    try:
        response = generate_improvement(
            ImprovementRequest(analysis=result, claim_number=claims[0], require_llm=True), settings
        )
        record |= {
            "ok": True,
            "status": response.status,
            "comparisons": len(response.suggestion.element_comparison),
            "strategies": [
                {"action_type": s.action_type, "title": s.title, "description": s.description}
                for s in response.suggestion.strategies
            ],
            "cautions": response.suggestion.cautions,
            "response": response.model_dump(mode="json"),
        }
    except (ProviderError, ValueError) as exc:
        record |= {"ok": False, "error": str(exc)}
    record["seconds"] = round(time.time() - started)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--label", required=True)
    parser.add_argument("--only", nargs="*", default=list(CASES))
    args = parser.parse_args()
    settings = Settings()
    out = ROOT / "data/outputs/llm_runs" / args.label
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "label": args.label,
        "provider": settings.improvement_provider,
        "model": settings.local_llm_model
        if settings.improvement_provider == "local_ollama"
        else settings.anthropic_model,
        "prune_invalid": settings.improvement_prune_invalid,
        "cases": [],
    }
    for app in args.only:
        record = run(app, settings)
        (out / f"{app}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        brief = {k: v for k, v in record.items() if k not in {"response", "cautions"}}
        brief["strategies"] = len(record.get("strategies", []))
        summary["cases"].append(brief)
        print(json.dumps(brief, ensure_ascii=False))
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
