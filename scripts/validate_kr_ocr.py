"""Reproducible rasterized-public-document OCR benchmark, not a real scanner corpus."""

import hashlib
import io
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

import pypdfium2 as pdfium
from pypdf import PdfReader, PdfWriter

from korean_prototype.kr_review.ingestion import read_document
from korean_prototype.kr_review.parsers import extract_claims, extract_office_action

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/outputs/kr_parity/ocr"


def rasterize(source, pages):
    doc = pdfium.PdfDocument(source.read_bytes())
    writer = PdfWriter()
    try:
        for index in pages:
            page = doc[index]
            bitmap = page.render(scale=300 / 72)
            try:
                stream = io.BytesIO()
                bitmap.to_pil().convert("RGB").save(stream, format="PDF", resolution=300)
                writer.add_page(PdfReader(io.BytesIO(stream.getvalue())).pages[0])
            finally:
                bitmap.close()
                page.close()
    finally:
        doc.close()
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def alignment_error(expected, actual):
    # Report this explicitly as alignment CER estimate, not minimal edit distance.
    a = re.sub(r"\s+", "", expected)
    b = re.sub(r"\s+", "", actual)
    errors = sum(
        max(i2 - i1, j2 - j1)
        for op, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
        if op != "equal"
    )
    return errors / max(1, len(a))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    truth = json.loads(
        (ROOT / "data/fixtures/korean/1020190000844.json").read_text(encoding="utf8")
    )
    pat = next(ROOT / f["path"] for f in truth["files"] if f["role"] == "patent")
    oa = next(
        ROOT / f["path"]
        for f in truth["files"]
        if f["role"] == "office_action" and f["path"].endswith(".pdf")
    )
    reports = []
    for source, kind, pages in [
        (pat, "patent", [2]),
        (oa, "office_action", list(range(len(PdfReader(oa).pages)))),
    ]:
        content = rasterize(source, pages)
        target = OUT / (kind + "_rasterized.pdf")
        target.write_bytes(content)
        document = read_document(content, target.name, kind)
        (OUT / (kind + "_ocr.txt")).write_text(document.text, encoding="utf8")
        (OUT / (kind + "_metadata.json")).write_text(
            json.dumps(document.metadata, ensure_ascii=False, indent=2), encoding="utf8"
        )
        expected = read_document(source.read_bytes(), source.name, kind)
        report = {
            "kind": kind,
            "source": str(source.relative_to(ROOT)),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "derived_fixture": str(target.relative_to(ROOT)),
            "derived_sha256": hashlib.sha256(content).hexdigest(),
            "derivation": "original public PDF pages rendered at 300 dpi and image-only PDF; original untouched",
            "original_page_numbers": [i + 1 for i in pages],
            "ocr_pages": document.metadata["ocr_pages"],
            "alignment_cer_estimate": alignment_error(
                "\n".join(expected.pages[i].text for i in pages), document.text
            ),
        }
        try:
            if kind == "patent":
                report["claims"] = [c.number for c in extract_claims(document)]
            else:
                grounds, refs = extract_office_action(document)
                report["grounds"] = [
                    {"claims": r.claims, "statute": r.statute_code} for r in grounds
                ]
                report["citations"] = [c.publication_number for c in refs]
                native_grounds, _ = extract_office_action(expected)
                expected_sentence = native_grounds[0].explanation.split("없습니다")[0] + "없습니다"
                actual_sentence = grounds[0].explanation.split("없습니다")[0] + "없습니다"
                report["rejection_sentence_alignment_cer_estimate"] = alignment_error(
                    expected_sentence, actual_sentence
                )
        except ValueError as exc:
            report["error"] = str(exc)
        reports.append(report)
        print(json.dumps(report, ensure_ascii=False), flush=True)
    # Mixed extraction must OCR only the rasterized claim page.
    writer = PdfWriter()
    reader = PdfReader(pat)
    scanned = PdfReader(OUT / "patent_rasterized.pdf")
    for i, page in enumerate(reader.pages):
        writer.add_page(scanned.pages[0] if i == 2 else page)
    mixed = io.BytesIO()
    writer.write(mixed)
    d = read_document(mixed.getvalue(), "mixed.pdf", "patent")
    reports.append(
        {
            "kind": "mixed_patent",
            "ocr_pages": d.metadata["ocr_pages"],
            "claims": [c.number for c in extract_claims(d)],
            "native_page_1_preserved": d.pages[0].text
            == read_document(pat.read_bytes(), pat.name, "patent").pages[0].text,
        }
    )
    # Independently exercise the mixed Office Action route as well.
    writer = PdfWriter()
    oa_reader = PdfReader(oa)
    oa_scanned = PdfReader(OUT / "office_action_rasterized.pdf")
    for i, page in enumerate(oa_reader.pages):
        writer.add_page(oa_scanned.pages[i] if i == 1 else page)
    mixed_oa = io.BytesIO()
    writer.write(mixed_oa)
    d = read_document(mixed_oa.getvalue(), "mixed_oa.pdf", "office_action")
    grounds, refs = extract_office_action(d)
    reports.append(
        {
            "kind": "mixed_office_action",
            "ocr_pages": d.metadata["ocr_pages"],
            "grounds": [{"claims": r.claims, "statute": r.statute_code} for r in grounds],
            "citations": [c.publication_number for c in refs],
        }
    )
    expected_refs = truth["rejections"][0]["citations"]
    for report in reports:
        if report["kind"] in {"patent", "mixed_patent"}:
            report["core_fields_pass"] = report.get("claims") == [1]
        else:
            report["core_fields_pass"] = (
                report.get("grounds") == [{"claims": [1], "statute": "KR_PATENT_ACT_29_2"}]
                and report.get("citations") == expected_refs
            )
    (OUT / "metrics.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf8"
    )
    assert all(r["core_fields_pass"] for r in reports), reports
    assert reports[2]["ocr_pages"] == [3] and reports[2]["native_page_1_preserved"]
    assert reports[3]["ocr_pages"] == [2]


if __name__ == "__main__":
    main()
