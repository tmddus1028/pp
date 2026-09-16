"""Isolated native PDF opening/text extraction; never repairs or saves a PDF."""

import json
import re
import sys

CLAIMS_HEADING = re.compile(r"what is claimed is\s*:", re.I)


def ordered_claim_text(chars, width, heading_required):
    """Recover interleaved Claim lines from glyph geometry, retaining all glyphs.

    Only used after a malformed inline Claims heading has been detected. The
    area above that heading remains full-width; lower columns are read in order.
    """
    prepared, space = [], False
    for char, box in chars:
        if char.isspace():
            space = True
        else:
            prepared.append(((" " if space else "") + char, box))
            space = False
    rows = []
    for char, box in sorted(prepared, key=lambda c: ((c[1][1] + c[1][3]) / 2, c[1][0])):
        if box[3] <= box[1]:
            continue
        y = (box[1] + box[3]) / 2
        if not rows or abs(rows[-1][0] - y) > 2:
            rows.append((y, []))
        rows[-1][1].append((char, box))

    def line(glyphs):
        return "".join(char for char, _ in sorted(glyphs, key=lambda c: c[1][0])).strip()

    boundary = next(
        (i for i, (_, row) in enumerate(rows) if CLAIMS_HEADING.search(line(row))), None
    )
    if heading_required and boundary is None:
        return None
    if boundary is None:
        # Preserve the page header as one line, before reading a continuation.
        boundary = next(
            (i for i, (_, row) in enumerate(rows) if re.match(r"\d+\.\s*[A-Z]", line(row))),
            None,
        )
    if boundary is None:
        return None
    prefix = [line(row) for _, row in rows[:boundary]]
    columns = [[], []]
    for _, row in rows[boundary:]:
        for column in (0, 1):
            glyphs = [c for c in row if ((c[1][0] + c[1][2]) / 2 >= width / 2) == bool(column)]
            if glyphs:
                columns[column].append(line(glyphs))
    two_columns = all(any(re.match(r"\d+\.\s*[A-Z]", row) for row in col) for col in columns)
    body = columns[0] + columns[1] if two_columns else [line(row) for _, row in rows[boundary:]]
    output = "\n".join(prefix + body)
    if not re.search(r"(?m)^\d+\.\s*[A-Z]", output):
        return None
    return output


def pymupdf_pages(path, max_pages):
    import pymupdf

    with pymupdf.open(path) as doc:
        if doc.needs_pass or doc.is_encrypted:
            raise ValueError("encrypted")
        if not 0 < len(doc) <= max_pages:
            return {"error": "page_limit"}
        pages, failed, layouts = [], [], []
        claim_layout = False
        for index in range(len(doc)):
            page = doc.load_page(index)  # An unreadable page tree tries the next engine.
            try:
                text = page.get_text("text")
                heading = CLAIMS_HEADING.search(text)
                broken = bool(
                    heading and not re.search(r"(?im)^\s*what is claimed is\s*:\s*$", text)
                )
                if broken or claim_layout:
                    chars = [
                        (
                            c["c"],
                            (
                                c["bbox"][0],
                                c["origin"][1] - 0.5,
                                c["bbox"][2],
                                c["origin"][1] + 0.5,
                            ),
                        )
                        for block in page.get_text("rawdict")["blocks"]
                        if "lines" in block
                        for line in block["lines"]
                        for span in line["spans"]
                        for c in span["chars"]
                    ]
                    ordered = ordered_claim_text(chars, page.rect.width, broken)
                    if ordered:
                        text, claim_layout = ordered, True
                        layouts.append(index + 1)
                pages.append(text)
            except Exception:
                pages.append("")
                failed.append(index + 1)
        return {"pages": pages, "failed": failed, "layouts": layouts}


def pdfium_pages(path, max_pages):
    from ctypes import byref, c_double

    import pypdfium2 as pdfium
    import pypdfium2.raw as raw

    with pdfium.PdfDocument(path) as doc:
        if raw.FPDF_GetSecurityHandlerRevision(doc) >= 0:
            raise ValueError("encrypted")
        if not 0 < len(doc) <= max_pages:
            return {"error": "page_limit"}
        pages, failed, layouts = [], [], []
        claim_layout = False
        for index in range(len(doc)):
            page = doc[index]
            try:
                textpage = page.get_textpage()
                try:
                    text = textpage.get_text_bounded()
                    heading = CLAIMS_HEADING.search(text)
                    broken = bool(
                        heading and not re.search(r"(?im)^\s*what is claimed is\s*:\s*$", text)
                    )
                    if broken or claim_layout:
                        chars = []
                        for i in range(textpage.count_chars()):
                            code = raw.FPDFText_GetUnicode(textpage, i)
                            if code:
                                x1, y1, x2, y2 = textpage.get_charbox(i)
                                x, y = c_double(), c_double()
                                if not raw.FPDFText_GetCharOrigin(textpage, i, byref(x), byref(y)):
                                    raise ValueError("Missing glyph origin")
                                chars.append((chr(code), (x1, -y.value - 0.5, x2, -y.value + 0.5)))
                        ordered = ordered_claim_text(chars, page.get_width(), broken)
                        if ordered:
                            text, claim_layout = ordered, True
                            layouts.append(index + 1)
                    pages.append(text)
                finally:
                    textpage.close()
            except Exception:
                pages.append("")
                failed.append(index + 1)
            finally:
                page.close()
        return {"pages": pages, "failed": failed, "layouts": layouts}


def open_native(path, max_pages):
    failures = []
    for engine, read in (("pymupdf", pymupdf_pages), ("pdfium", pdfium_pages)):
        try:
            result = read(path, max_pages)
            return {**result, "engine": engine, "failures": failures}
        except Exception as exc:
            # Library errors may contain source bytes. Record engine/type only.
            failures.append(f"{engine}: {type(exc).__name__}")
    return {"engine": None, "pages": [], "failed": [], "layouts": [], "failures": failures}


if __name__ == "__main__":
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    request = json.load(sys.stdin)
    print(json.dumps(open_native(request["path"], request["max_pages"]), ensure_ascii=True))
