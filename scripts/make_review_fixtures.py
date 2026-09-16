"""Synthetic UI evidence fixtures; never label these as an actual Office Action."""

from io import BytesIO
from pathlib import Path
from textwrap import wrap

import pypdfium2
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/pdf_review"


def text_pdf(pages):
    stream = BytesIO()
    pdf = canvas.Canvas(stream, pagesize=(612, 792), invariant=True)
    for lines in pages:
        pdf.setFont("Helvetica", 14)
        y = 750
        for line in lines:
            for part in wrap(line, 78) or [""]:
                pdf.drawString(40, y, part)
                y -= 22
        pdf.showPage()
    pdf.save()
    return stream.getvalue()


def scan_pdf(data):
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=(612, 792), invariant=True)
    with pypdfium2.PdfDocument(data) as document:
        for i in range(len(document)):
            page = document[i]
            bitmap = page.render(scale=300 / 72)
            image = bitmap.to_pil().convert("RGB")
            pdf.drawImage(ImageReader(image), 0, 0, width=612, height=792)
            image.close()
            bitmap.close()
            page.close()
            pdf.showPage()
    pdf.save()
    return output.getvalue()


def main():
    FIXTURES.mkdir(parents=True, exist_ok=True)
    oa = text_pdf(
        [
            [
                "SYNTHETIC OFFICE ACTION - UI REGRESSION",
                "Application No. 14/623,904",
                "",
                "Claim Rejections - 35 U.S.C. 112",
                "Claims 1, 3-4, 6-7, 9-10, 12-19 are rejected under 35 U.S.C. 112 as indefinite.",
                "The examiner requests clarification of the claim language.",
                "This fixture reconstructs user-supplied facts, not actual examiner reasoning.",
            ],
            [
                "SYNTHETIC OFFICE ACTION - UI REGRESSION",
                "Application No. 14/623,904",
                "",
                "Claim Rejections - 35 U.S.C. 103",
                "Claims 1-19 are rejected under 35 U.S.C. 103(a) as unpatentable over",
                "Lombardi et al. (WO2009/013126 A1) in view of Bendiera et al. (WO2008/074749 A1)",
                "and Hout et al. (WO2013/119950 A2), and further in view of",
                "Greco et al., Molecular and Cellular Endocrinology (2010), Vol. 321(1), pp. 44-49;",
                "and Lipska et al., BMC Cancer (2009), 9:436, pp. 1-9.",
                "The examiner discusses the combined teachings.",
                "Conclusion",
                "End of synthetic fixture.",
            ],
        ]
    )
    patent = text_pdf(
        [
            [
                "SYNTHETIC PATENT - UI REGRESSION",
                "FIG. 1",
                "",
                "[0018] A sensor transmits an electrical signal to a controller.",
                "[0019] The controller stores the measured data in memory.",
            ],
            [
                "Claims",
                "1. A system comprising a controller and a sensor.",
                "2. The system of claim 1, wherein the sensor measures temperature.",
                "3. The system of claim 2, wherein the controller stores the measurement.",
                "4. A method comprising receiving a measurement from a sensor.",
            ],
        ]
    )
    small_oa = text_pdf(
        [
            [
                "SYNTHETIC OFFICE ACTION - UI REGRESSION",
                "",
                "Claim 1 is rejected under 35 U.S.C. 112(b) as indefinite.",
                "The examiner refers to paragraph [0018] and FIG. 1 of the specification.",
                "The phrase controller requires clarification.",
            ]
        ]
    )
    for name, data in [
        ("office_action_reconstructed.pdf", oa),
        ("patent.pdf", patent),
        ("office_action_support.pdf", small_oa),
    ]:
        (FIXTURES / name).write_bytes(data)
    (FIXTURES / "patent_scan.pdf").write_bytes(scan_pdf(patent))
    (FIXTURES / "office_action_scan.pdf").write_bytes(scan_pdf(small_oa))
    print("Created explicitly synthetic PDF review fixtures.")


if __name__ == "__main__":
    main()
