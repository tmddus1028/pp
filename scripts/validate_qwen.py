"""Preflight by default; --live makes at most two paid Qwen requests per run."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from backend.config import Settings
from backend.errors import ProviderError
from backend.improvements.models import ImprovementRequest
from backend.improvements.providers import QwenImprovementProvider
from backend.improvements.retrieval import retrieved_context
from backend.improvements.revision import review_revision
from backend.improvements.revision_models import RevisionRequest
from backend.improvements.service import generate_improvement
from backend.jurisdictions.korean import analyze_korean
from backend.schemas import AnalysisResult

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="Send evidence to Qwen (up to 2 paid calls)"
    )
    parser.add_argument(
        "--analysis-json",
        type=Path,
        help="Existing US/KR AnalysisResult; defaults to the public KR fixture",
    )
    parser.add_argument("--claim", type=int, default=1)
    parser.add_argument("--rejection", default="R1")
    parser.add_argument(
        "--revised-file",
        type=Path,
        help="UTF-8 revision; default is unchanged claim as a transport baseline",
    )
    args = parser.parse_args()
    config = Settings(_env_file=ROOT / ".env")
    config.improvement_provider = "qwen"
    # This API comparison does not start any local embedding model.
    config.local_embedding_model = ""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = ROOT / "data/outputs/qwen" / stamp
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "live_requested": args.live,
        "provider": "qwen",
        "model": config.qwen_model,
        "checks": [],
        "live_completed": False,
    }
    try:
        if args.analysis_json:
            analysis = AnalysisResult.model_validate_json(
                args.analysis_json.read_text(encoding="utf-8")
            )
        else:
            folder = ROOT / "korean_prototype/data/kr_1020190000844"
            analysis = analyze_korean(
                (folder / "KR20190025857A.pdf").read_bytes(),
                "KR20190025857A.pdf",
                (folder / "office_action_20190409.xml").read_bytes(),
                "office_action_20190409.xml",
            )
        before = analysis.model_dump_json()
        request = ImprovementRequest(
            analysis=analysis,
            claim_number=args.claim,
            rejection_id=args.rejection,
            require_llm=True,
        )
        claim = next(c for c in analysis.patent.claims if c.claim_number == args.claim)
        context, sources, digest, _, _ = retrieved_context(
            request, [("selected_claim", claim.text)]
        )
        report.update(
            analysis_id=analysis.analysis_id,
            analysis_sha256=hashlib.sha256(before.encode()).hexdigest(),
            jurisdiction=context["jurisdiction"],
            evidence_hash=digest,
            source_count=len(sources),
            context_chars=len(json.dumps(context, ensure_ascii=False)),
        )
        report["checks"].append("Local document analysis and evidence retrieval completed")
        QwenImprovementProvider(config).endpoint()
        if not args.live:
            report["status"] = "READY_NOT_CALLED"
            report["checks"].append(
                "Configuration present; credentials and model access NOT verified"
            )
            return 0
        started = perf_counter()
        improvement = generate_improvement(request, config)
        report["improvement_seconds"] = round(perf_counter() - started, 2)
        (output / "improvement.json").write_text(
            improvement.model_dump_json(indent=2), encoding="utf-8"
        )
        report["checks"].append("Live improvement response passed schema and evidence gates")
        text = args.revised_file.read_text(encoding="utf-8") if args.revised_file else claim.text
        report["revision_input"] = (
            "user-provided test revision"
            if args.revised_file
            else "unchanged claim transport baseline"
        )
        started = perf_counter()
        revision = review_revision(
            RevisionRequest(**request.model_dump(), revised_text=text), config
        )
        report["revision_seconds"] = round(perf_counter() - started, 2)
        (output / "revision.json").write_text(revision.model_dump_json(indent=2), encoding="utf-8")
        if analysis.model_dump_json() != before:
            raise ValueError("Original analysis changed")
        report["checks"].append(
            "Live revision passed schema/evidence gates; original analysis unchanged"
        )
        report.update(
            status="TRANSPORT_AND_GROUNDING_PASS",
            live_completed=True,
            quality_review="NOT_EVALUATED",
        )
        return 0
    except (ProviderError, ValueError, OSError, StopIteration) as exc:
        report["status"] = "BLOCKED_OR_FAILED"
        report["error"] = (
            str(exc)
            if isinstance(exc, ProviderError)
            else "Input or local validation error; check fixture and claim selection"
        )
        return 2
    finally:
        (output / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print("Report:", output / "report.json")


if __name__ == "__main__":
    raise SystemExit(main())
