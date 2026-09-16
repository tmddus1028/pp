"""Read original PDF pairs through the live multipart API and compare explicit labels."""

import argparse
import hashlib
import json
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    reports = []
    for number, application, count in [(1, "14/623,904", 19), (2, "15/914,356", 20), (3, "17/708,932", 20)]:
        paths = [args.input / f"pp_{kind}{number}.pdf" for kind in ("ex", "vd")]
        data = [p.read_bytes() for p in paths]
        response = httpx.post(
            "http://127.0.0.1:8000/analyze/files",
            files={key: (p.name, b, "application/pdf") for key, p, b in zip(["patent", "office_action"], paths, data)},
            timeout=600,
        )
        result = response.json()
        (args.output / f"pair-{number}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        report = {"application": application, "http_status": response.status_code, "sources": [{"path": str(p), "sha256": hashlib.sha256(b).hexdigest()} for p, b in zip(paths, data)], "checks": {}}
        checks = report["checks"]
        def check(name, actual, expected):
            checks[name] = {"actual": actual, "expected": expected, "pass": actual == expected}
        if response.status_code == 200:
            summary = result["claim_summary"]
            check("claims", [c["claim_number"] for c in result["patent"]["claims"]], list(range(1, count + 1)))
            check("global_direct", summary["direct_rejected_claims"], list(range(1, 20)) if number == 1 else list(range(1, 21)) if number == 2 else list(range(1, 15)) + [17, 18, 19])
            check("global_dependency", summary["dependency_impacted_claims"], [] if number < 3 else [15, 16])
            check("objected", summary["objected_claims"], [15, 16] if number == 3 else [])
            check("allowed", summary["allowed_claims"], [])
            check("canceled", summary["canceled_claims"], [20] if number == 3 else [])
            rejected = [r for r in result["rejections"] if r["action_type"] == "rejection"]
            check("rejection_count", len(rejected), {1: 2, 2: 3, 3: 5}[number])
            check("unique_relied_citations", len([c for c in result["citations"] if c["citation_role"] == "relied_upon"]), {1: 5, 2: 5, 3: 7}[number])
            expected = {
                1: [[1,3,4,6,7,9,10,12,13,14,15,16,17,18,19], list(range(1,20))],
                2: [list(range(1,13)) + [20], [13,17,18,19], [14,15,16]],
                3: [[1,2,3,4,6,8,17,18,19], [5,6], [7,9], [10,11], [12,13,14]],
            }[number]
            check("rejection_claims", [r["claims"] for r in rejected], expected)
            if number == 1:
                check("R1_dependency", result["impacts"][0]["dependency_impacted_claims"], [2,5,8,11])
                check("R2_dependency", result["impacts"][1]["dependency_impacted_claims"], [])
            if number == 2:
                check("pages", [len(d["pages"]) for d in result["documents"]], [47,13])
            if number == 3:
                for role, names in [("supporting_evidence", ["Wei"]), ("not_relied_upon", ["Biyikli", "Oda et al."])]:
                    check(role, sorted(c["display_name"] for c in result["citations"] if c["citation_role"] == role), names)
            documents = {d["document_id"]: d for d in result["documents"]}
            failures = []
            def visit(value):
                if isinstance(value, dict):
                    if {"document_id","start","end","text","page_numbers"} <= value.keys():
                        doc = documents[value["document_id"]]
                        if value["text"] != doc["text"][value["start"]:value["end"]]: failures.append(value["start"])
                        if value["page_numbers"] != [p["number"] for p in doc["pages"] if p["start"] < value["end"] and p["end"] > value["start"]]: failures.append(value["start"])
                    for child in value.values(): visit(child)
                elif isinstance(value, list):
                    for child in value: visit(child)
            visit(result)
            check("evidence_mismatches", failures, [])
        reports.append(report)
        (args.output / "golden-checks.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
        print(application, response.status_code, {k:v for k,v in checks.items() if not v["pass"]}, flush=True)
    raise SystemExit(0 if all(r["http_status"] == 200 and all(c["pass"] for c in r["checks"].values()) for r in reports) else 1)


if __name__ == "__main__":
    main()
