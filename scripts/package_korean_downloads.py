"""Create a user-facing ZIP of originals, provenance and candid validation results."""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from scripts.prepare_korean_downloads import OUT, SOURCE, save_json


def main():
    name = "Patent_Review_KR_Data_20260917"
    target = OUT.parent / name
    target.mkdir(exist_ok=True)
    cases = json.loads((OUT / "validation/paired_cases.json").read_text(encoding="utf-8"))
    files = []

    def copy(source, relative, role):
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        content = destination.read_bytes()
        files.append(
            {
                "file": relative.as_posix(),
                "role": role,
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )

    for case in cases:
        base = (
            Path("01_verified" if case["status"] == "PASS" else "02_needs_work")
            / case["application"]
        )
        for key, role in [
            ("patent_file", "patent"),
            ("oa_xml", "office_action_xml"),
            ("oa_pdf", "office_action_pdf"),
        ]:
            source = OUT / case[key]
            copy(source, base / source.name, role)
        save_json(target / base / "case_result.json", case)
    for source in (OUT / "publications").glob("KR2015*.pdf"):
        copy(source, Path("01_verified/1020190000844/references") / source.name, "reference")
    copy(
        SOURCE / "claim_oa_comparison.json",
        Path("01_verified/1020190000844/claim_oa_comparison.json"),
        "version_evidence",
    )
    for source in OUT.glob("*.zip"):
        copy(source, Path("03_official_archives") / source.name, "official_sample_archive")
    for source in (OUT / "validation").iterdir():
        if source.is_file():
            copy(source, Path("04_validation") / source.name, "validation")
    copy(OUT / "README.md", Path("README.md"), "instructions")
    save_json(
        target / "sources.json",
        {
            "official_samples": json.loads(
                (OUT / "official_downloads.json").read_text(encoding="utf-8")
            ),
            "publications": json.loads(
                (OUT / "publication_downloads.json").read_text(encoding="utf-8")
            ),
        },
    )
    save_json(
        target / "manifest.json",
        {"files": files, "paired_case_statuses": {c["application"]: c["status"] for c in cases}},
    )
    archive_path = target.with_suffix(".zip")
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(target.rglob("*")):
            if path.is_file():
                archive.write(path, Path(name) / path.relative_to(target))
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        for entry in files:
            assert (
                hashlib.sha256(archive.read(name + "/" + entry["file"])).hexdigest()
                == entry["sha256"]
            )
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    desktop = Path.home() / "Desktop" / archive_path.name
    shutil.copyfile(archive_path, desktop)
    assert hashlib.sha256(desktop.read_bytes()).hexdigest() == digest
    desktop.with_suffix(".zip.sha256").write_text(
        digest + "  " + desktop.name + "\n", encoding="ascii"
    )
    print(desktop)
    print(f"bytes={desktop.stat().st_size}; sha256={digest}")


if __name__ == "__main__":
    main()
