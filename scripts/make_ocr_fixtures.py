"""Create explicitly synthetic patent OCR fixtures; no real case assertions."""

import json
from io import BytesIO
from pathlib import Path

import pypdfium2
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/ocr"
PAGES = [
    [
        "SYNTHETIC OFFICE ACTION - OCR TEST",
        "Application No. 14/623,904",
        "Claim Rejections - 35 U.S.C. § 112",
        "Claims 1-19 are rejected under 35 U.S.C. 112(b) as indefinite.",
        "Claim 1 does not identify the antecedent basis for the controller.",
        "The same issue applies to the dependent claims.",
        "This is a fabricated test document, not an actual USPTO action.",
    ],
    [
        "SYNTHETIC OFFICE ACTION - OCR TEST",
        "Application No. 14/623,904",
        "Claim Rejections - 35 U.S.C. § 103",
        "Claims 1-19 are rejected under 35 U.S.C. 103 as being",
        "unpatentable over Smith (US 2010/0123456 A1) in view of",
        "Johnson (U.S. Patent No. 8,765,432 B2).",
        "Smith describes a controller and Johnson describes a sensor.",
        "This is a fabricated test document, not an actual USPTO action.",
    ],
]


def draw_text(pdf, lines):
    pdf.setFont("Times-Roman", 16)
    for i, line in enumerate(lines):
        pdf.drawString(40, 740 - 36 * i, line)


def make_fixtures():
    FIXTURES.mkdir(parents=True, exist_ok=True)
    text_pdf = BytesIO()
    pdf = canvas.Canvas(text_pdf, pagesize=(612, 792), invariant=1)
    for lines in PAGES:
        draw_text(pdf, lines)
        pdf.showPage()
    pdf.save()
    (FIXTURES / "office_action_text.pdf").write_bytes(text_pdf.getvalue())
    with pypdfium2.PdfDocument(text_pdf.getvalue()) as source:
        for name, scan_pages in [
            ("office_action_scan.pdf", {0, 1}),
            ("office_action_mixed.pdf", {1}),
        ]:
            output = BytesIO()
            pdf = canvas.Canvas(output, pagesize=(612, 792), invariant=1)
            for index, lines in enumerate(PAGES):
                if index in scan_pages:
                    page = source[index]
                    bitmap = page.render(scale=300 / 72)
                    image = bitmap.to_pil().convert("L")
                    pdf.drawImage(ImageReader(image), 0, 0, width=612, height=792)
                    image.close()
                    bitmap.close()
                    page.close()
                else:
                    draw_text(pdf, lines)
                pdf.showPage()
            pdf.save()
            (FIXTURES / name).write_bytes(output.getvalue())
    (FIXTURES / "expected_pages.json").write_text(
        json.dumps(["\n".join(p) for p in PAGES], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    claims = ["Claims", "1. A control system comprising a controller and a sensor."]
    claims.extend(
        f"{n}. The control system of claim 1, wherein the sensor measures signal {n}."
        for n in range(2, 20)
    )
    (FIXTURES / "claims.txt").write_text("\n".join(claims), encoding="utf-8")
    print(f"Created text, image-only and mixed fixtures in {FIXTURES}")


if __name__ == "__main__":
    make_fixtures()
