"""Record real downloaded-data outcomes, including unsupported cases and defects."""

import hashlib
import zipfile
from collections import Counter
from pathlib import Path

import httpx
from pypdf import PdfReader

from backend.schemas import AnalysisResult
from korean_prototype.kr_review.ingestion import read_document
from korean_prototype.kr_review.parsers import extract_office_action
from scripts.prepare_korean_downloads import OUT, PUBLICATIONS, save_json


def evidence_checks(value, documents):
    count = 0
    if isinstance(value, dict):
        if {"document_id", "text", "start", "end", "page_numbers"} <= value.keys():
            document = documents[value["document_id"]]
            assert document["text"][value["start"] : value["end"]] == value["text"]
            assert value["page_numbers"] == [
                p["number"]
                for p in document["pages"]
                if p["start"] < value["end"] and p["end"] > value["start"]
            ]
            count += 1
        for child in value.values():
            count += evidence_checks(child, documents)
    elif isinstance(value, list):
        count += sum(evidence_checks(child, documents) for child in value)
    return count


def main():
    validation = OUT / "validation"
    validation.mkdir(exist_ok=True)
    records = []
    with httpx.Client(timeout=120) as client:
        for application, publication in PUBLICATIONS.items():
            patent = OUT / "publications" / (publication + ".pdf")
            oa = next((OUT / "official_samples").glob(application + "*/*.xml"))
            pdf = oa.with_suffix(".pdf")
            record = {
                "application": application,
                "publication": publication,
                "patent_file": str(patent.relative_to(OUT)),
                "oa_xml": str(oa.relative_to(OUT)),
                "oa_pdf": str(pdf.relative_to(OUT)),
                "patent_pages": len(PdfReader(patent).pages),
                "oa_pdf_pages": len(PdfReader(pdf).pages),
                "version_status": "existing claim/OA comparison available"
                if application.endswith("844")
                else "same application verified; historical claim version not fully verified",
            }
            response = client.post(
                "http://127.0.0.1:8000/analyze/files?jurisdiction=KR",
                files={
                    "patent": (patent.name, patent.read_bytes(), "application/pdf"),
                    "office_action": (oa.name, oa.read_bytes(), "application/xml"),
                },
            )
            record["http_status"] = response.status_code
            body = response.json()
            save_json(validation / (application + "_api.json"), body)
            if response.is_success:
                AnalysisResult.model_validate(body)
                record.update(
                    claim_count=len(body["patent"]["claims"]),
                    direct=body["claim_summary"]["direct_rejected_claims"],
                    dependency=body["claim_summary"]["dependency_impacted_claims"],
                    unknown=body["claim_summary"]["unknown_claims"],
                    statutes=[r["statute"] for r in body["rejections"]],
                    citations=[c["publication_number"] for c in body["citations"]],
                    evidence_checks=evidence_checks(
                        body, {d["document_id"]: d for d in body["documents"]}
                    ),
                )
                if application == "1020190000844":
                    assert record["claim_count"] == 1 and record["direct"] == [1]
                    assert record["statutes"] == ["특허법 제29조제2항"]
                    assert set(record["citations"]) == {
                        "KR20150096573A",
                        "KR20150090348A",
                        "KR20150093093A",
                    }
                    assert body["patent"]["claims"][0]["evidence"]["page_numbers"] == [3]
                    record["status"] = "PASS"
                else:
                    assert record["claim_count"] == 16 and record["direct"] == list(range(1, 11))
                    assert record["statutes"] == ["특허법 제42조제4항제2호"]
                    claim6 = next(c for c in body["patent"]["claims"] if c["claim_number"] == 6)
                    record["status"] = "PARTIAL_FAIL"
                    record["defects"] = [
                        {
                            "claim": 6,
                            "actual_parents": claim6["depends_on"],
                            "expected_parents": [1],
                            "source_text": claim6["text"],
                            "reason": "PDF page header is inside Claim 6, so the existing Korean dependency parser misses the opening '청구항 1항에 있어서'.",
                        }
                    ]
                    assert claim6["depends_on"] != [1]
            else:
                record["status"] = "UNSUPPORTED"
                record["error"] = body.get("detail", body)
            records.append(record)
            print(application, record["status"], flush=True)
    save_json(validation / "paired_cases.json", records)

    # Additional archive is an OA-only ingestion/extraction check, not 178 paired analyses.
    rows = []
    with zipfile.ZipFile(OUT / "kipris_patent_oa_2015.zip") as archive:
        for name in archive.namelist():
            if not name.endswith(".xml"):
                continue
            row = {"member": name}
            try:
                document = read_document(archive.read(name), Path(name).name, "office_action")
                rejections, citations = extract_office_action(document)
                row.update(
                    status="EXTRACTION_COMPLETED_NOT_ACCURACY_VALIDATED",
                    rejections=len(rejections),
                    citations=len(citations),
                )
            except ValueError as exc:
                row.update(status="UNSUPPORTED", error=str(exc))
            rows.append(row)
    save_json(
        validation / "oa_only_2015.json",
        {"counts": dict(Counter(r["status"] for r in rows)), "cases": rows},
    )
    print("OA-only sample:", dict(Counter(r["status"] for r in rows)), flush=True)

    # Downloaded PDF/XML originals are never rewritten.
    originals = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.suffix in {".pdf", ".xml", ".zip"}:
            raw = path.read_bytes()
            originals.append(
                {
                    "file": str(path.relative_to(OUT)),
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
    save_json(validation / "original_hashes.json", originals)


if __name__ == "__main__":
    main()
