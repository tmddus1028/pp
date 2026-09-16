import argparse
from pathlib import Path

from backend.config import Settings
from backend.errors import DocumentError, ExtractionError, ProviderError
from backend.ingestion.adapters import LocalAdapter
from backend.service import analyze


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze a local patent and Office Action pair")
    parser.add_argument("--patent", type=Path, required=True)
    parser.add_argument("--office-action", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/outputs/analysis.json"))
    parser.add_argument("--provider", choices=["local", "openai", "azure"])
    args = parser.parse_args()
    settings = Settings(**({"llm_provider": args.provider} if args.provider else {}))
    adapter = LocalAdapter(settings)
    try:
        for path in [args.patent, args.office_action]:
            if path.stat().st_size > settings.max_upload_mb * 1024 * 1024:
                raise DocumentError("입력 파일 크기 제한을 초과했습니다.")
        result = analyze(
            adapter.read(args.patent.read_bytes(), args.patent.name, "patent"),
            adapter.read(args.office_action.read_bytes(), args.office_action.name, "office_action"),
            settings,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    except (OSError, DocumentError, ExtractionError, ProviderError) as exc:
        parser.exit(1, f"Analysis failed: {exc}\n")
    print(
        f"Saved {args.output}: {len(result.patent.claims)} claims, {len(result.rejections)} actions"
    )
    for warning in result.warnings:
        print(f"Review: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
