"""Freeze manually transcribed 2019 claims/OA labels; never derive labels from a parser."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/downloads/Patent_Review_KR_Data_20260917"
OUT = ROOT / "data/fixtures/korean"


def main():
    # Read from the source documents before implementation. Ground numbering
    # follows the examiner's top-level reasons, including description-only R1.
    cases = [
        (
            "1020190000844",
            1,
            {},
            [("29_2", [1], ["KR20150096573A", "KR20150090348A", "KR20150093093A"])],
            "2019-04-09",
        ),
        (
            "1020190000874",
            9,
            {2: [1], 3: [1], 4: [1], 6: [5], 7: [5], 9: [8]},
            [
                ("42_4_2", list(range(5, 8)), []),
                ("29_2", list(range(1, 10)), ["KR20070073517A", "KR20100021334A"]),
            ],
            "2019-04-01",
        ),
        (
            "1020190000902",
            16,
            {
                2: [1],
                3: [2],
                4: [1],
                5: [1],
                6: [1],
                7: [1],
                8: [7],
                9: [7],
                10: [1],
                12: [11],
                13: [12],
                14: [12],
                15: [12],
                16: [11],
            },
            [("42_4_2", list(range(1, 11)), [])],
            "2019-03-25",
        ),
        (
            "1020190000903",
            1,
            {},
            [("42_4_2", [1], []), ("29_2", [1], ["JP2002017337A", "JPH1057031A"])],
            "2019-02-25",
        ),
        (
            "1020190000948",
            9,
            {4: [2, 3], 7: [5, 6], 8: [7], 9: [7]},
            [
                ("42_3_1", [], []),
                ("42_4_1", list(range(1, 10)), []),
                ("29_1_2", list(range(1, 10)), ["npl:pharmacognmag51221262009"]),
                ("29_2", list(range(1, 10)), ["npl:pharmacognmag51221262009"]),
            ],
            "2019-01-15",
        ),
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    for application, count, deps, grounds, date in cases:
        folder = next(p for p in DATA.glob(f"*/*{application}") if p.is_dir())
        files = []
        paths = list(folder.rglob("*"))
        if application == "1020190000874":
            paths += list((OUT / "references").glob("KR*.pdf"))
        for p in sorted(paths):
            if p.suffix not in {".pdf", ".xml"}:
                continue
            files.append(
                {
                    "path": p.relative_to(ROOT).as_posix(),
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    "role": "office_action"
                    if p.name.startswith(application)
                    else "patent"
                    if p.name.startswith("KR2019")
                    else "reference",
                }
            )
        direct = sorted({n for _, numbers, _ in grounds for n in numbers})
        truth = {
            "application_number": application,
            "office_action_date": date,
            "label_method": "manual transcription of publication claims and examiner numbered grounds; not parser output",
            "version_status": "uncertain",
            "sources": "data/downloads/Patent_Review_KR_Data_20260917/sources.json",
            "files": files,
            "claims": list(range(1, count + 1)),
            "dependencies": {str(n): deps.get(n, []) for n in range(1, count + 1)},
            "rejections": [
                {"statute_code": "KR_PATENT_ACT_" + law, "claims": numbers, "citations": citations}
                for law, numbers, citations in grounds
            ],
            "statuses": {
                "rejected": direct,
                "pending": sorted(set(range(1, count + 1)) - set(direct)),
            },
        }
        target = OUT / (application + ".json")
        if target.exists():
            raise RuntimeError(f"Already frozen: {target}")
        target.write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
