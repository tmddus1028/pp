"""Read-only, case-specific feasibility checks; not a Korean production parser.

Run from the project root: uv run python data/research/kr_1020190000844/probe.py
"""

import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[2]))

from backend.errors import DocumentError  # noqa: E402
from backend.ingestion.adapters import LocalAdapter, from_text  # noqa: E402
from backend.office_action.rejection_extractor import extract_local  # noqa: E402
from backend.patent.claim_parser import parse_claims  # noqa: E402


def write_json(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def comparison_text(value):
    # Comparison only: preserve the original PDFs, XML, and extracted source strings.
    return re.sub(r"[\s,;.]", "", value)


def main():
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    files = manifest["documents"] + [manifest["office_action"]]
    for source in files:
        path = ROOT / source.get("local_pdf", source.get("local_file"))
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"], path.name

    xml_path = ROOT / "office_action_20190409.xml"
    xml = ET.parse(xml_path).getroot()

    def field(tag):
        element = next(el for el in xml.iter() if el.tag.rsplit("}", 1)[-1] == tag)
        return "".join(element.itertext()).strip()

    oa = field("RejectionLawDetail")
    pdf_path = ROOT / "KR20190025857A.pdf"
    reader = PdfReader(pdf_path)
    page = reader.pages[2].extract_text()
    claim = page.split("청구항 1", 1)[1].split("발명의 설명", 1)[0].strip()
    recitation = oa.split("청구항 1 발명은 (전제부) ", 1)[1].split("에 관한 것이나,", 1)[0]
    preamble, components = claim.split("상기 쿠폰 관리 장치는,", 1)
    sections = components.split(";")
    sections[6] = sections[6].removeprefix(" 및").strip()
    sections[6] = sections[6].rsplit("를 포함하는 전자쿠폰 시스템.", 1)[0]
    oa_parts = re.split("[①②③④⑤⑥⑦]", recitation)
    oa_parts[1] = oa_parts[1].strip().removeprefix("상기 쿠폰 관리 장치는 ")
    oa_parts[6] = oa_parts[6].strip().removesuffix("및")
    oa_parts[7] = oa_parts[7].rsplit("를 포함하는 전자쿠폰 시스템", 1)[0]
    comparisons = [
        {"part": "preamble", "match": comparison_text(preamble) == comparison_text(oa_parts[0])}
    ]
    comparisons.extend(
        {
            "part": f"component_{index}",
            "match": comparison_text(a) == comparison_text(b),
        }
        for index, (a, b) in enumerate(zip(sections, oa_parts[1:], strict=True), 1)
    )
    write_json(
        "claim_oa_comparison.json",
        {
            "purpose": "Case-specific text comparison, not proof of complete prosecution history",
            "claim_source": "KR20190025857A.pdf, page 3",
            "oa_source": "office_action_20190409.xml, RejectionLawDetail",
            "original_claim_text": claim,
            "original_oa_claim_recitation": recitation,
            "normalization": "Compare components after removing whitespace, punctuation and OA labels",
            "comparisons": comparisons,
        },
    )

    compatibility = {}
    adapter = LocalAdapter()
    try:
        adapter.read(xml_path.read_bytes(), xml_path.name, "office_action")
        compatibility["xml_upload"] = "accepted"
    except DocumentError as exc:
        compatibility["xml_upload"] = {"error": str(exc)}
    try:
        document = adapter.read(pdf_path.read_bytes(), pdf_path.name, "patent")
        compatibility["pdf_ingestion"] = {
            "pages": len(document.pages),
            "text_chars": len(document.text),
            "ocr_used": document.metadata.ocr_used,
            "claim_phrase_preserved": "하나 이상의 행사와 매칭되고" in document.text,
        }
        try:
            claims = parse_claims(document)
            compatibility["claim_parser"] = {"claim_numbers": [c.claim_number for c in claims]}
        except DocumentError as exc:
            compatibility["claim_parser"] = {"error": str(exc)}
    except DocumentError as exc:
        compatibility["pdf_ingestion"] = {"error": str(exc)}

    rejections, warnings = extract_local(from_text(oa, "oa_rejection_probe.txt", "office_action"))
    compatibility["oa_text_probe"] = {"rejections": len(rejections), "warnings": warnings}
    write_json(
        "checks.json",
        {
            "application_number": field("ApplicationNumberText"),
            "office_action_date": field("DocumentDate"),
            "title": field("InventionTitle"),
            "publication_pdf_pages": len(reader.pages),
            "application_number_present_on_pdf_cover": "10-2019-0000844"
            in reader.pages[0].extract_text(),
            "claim_page": 3,
            "examination_claims": field("ExaminationClaims"),
            "statute_present_in_oa": "특허법 제29조제2항" in oa,
            "relied_publications_from_oa": re.findall(
                r"인용발명 \d : 공개특허공보 제([\d-]+)호", oa
            ),
            "source_hashes_verified": True,
            "all_8_claim_components_match_after_format_normalization": all(
                item["match"] for item in comparisons
            ),
            "compatibility": compatibility,
            "azure_inference_tested": False,
            "production_code_changed": False,
        },
    )
    print((ROOT / "checks.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
