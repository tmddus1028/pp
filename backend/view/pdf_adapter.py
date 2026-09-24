"""Display-only PDF coordinates. Never changes analysis text or source bytes."""

import base64
import math
import threading
import unicodedata
from difflib import SequenceMatcher
from io import BytesIO

import pypdfium2 as pdfium
import pypdfium2.raw as raw

# Streamlit sessions share a process; PDFium requires serialized native calls.
PDF_LOCK = threading.RLock()


def canonical(text):
    chars, offsets = [], []
    for offset, value in enumerate(text):
        for char in unicodedata.normalize("NFKC", value).casefold():
            if char.isalnum():
                chars.append(char)
                offsets.append(offset)
    return "".join(chars), offsets


def _normalized_box(page, box):
    """Use PDFium's own page-to-device transform, including crop and rotation."""
    from ctypes import byref, c_int

    width, height = page.get_size()
    device_width, device_height = round(width * 10), round(height * 10)
    points = []
    for x, y in [(box[0], box[1]), (box[0], box[3]), (box[2], box[1]), (box[2], box[3])]:
        dx, dy = c_int(), c_int()
        if not raw.FPDF_PageToDevice(
            page, 0, 0, device_width, device_height, 0, x, y, byref(dx), byref(dy)
        ):
            return None
        points.append((dx.value / device_width, dy.value / device_height))
    result = [
        min(x for x, _ in points),
        min(y for _, y in points),
        max(x for x, _ in points),
        max(y for _, y in points),
    ]
    result = [max(0, min(1, value)) for value in result]
    return result if result[2] > result[0] and result[3] > result[1] else None


def page_index(data: bytes, number: int, ocr_words=None):
    """Return a canonical character stream with a bbox for each character."""
    chars, boxes = [], []
    if ocr_words:
        for word in ocr_words:
            value, _ = canonical(word["text"])
            chars.extend(value)
            boxes.extend([word["bbox"]] * len(value))
        return "".join(chars), boxes, "ocr"
    with PDF_LOCK, pdfium.PdfDocument(data) as pdf:
        page = pdf[number - 1]
        textpage = page.get_textpage()
        try:
            for i in range(textpage.count_chars()):
                code = raw.FPDFText_GetUnicode(textpage, i)
                if not code:
                    continue
                value, _ = canonical(chr(code))
                if not value:
                    continue
                box = _normalized_box(page, textpage.get_charbox(i))
                chars.extend(value)
                boxes.extend([box] * len(value))
        finally:
            textpage.close()
            page.close()
    return "".join(chars), boxes, "text_layer"


def align_page(page_text: str, index):
    source, offsets = canonical(page_text)
    target, boxes, method = index
    mapping = {}
    for block in SequenceMatcher(None, source, target, autojunk=False).get_matching_blocks():
        if block.size < 3:
            continue
        for i in range(block.size):
            box = boxes[block.b + i]
            if box:
                mapping[offsets[block.a + i]] = box
    return mapping, method


def merge_boxes(boxes):
    """Small line rectangles; never bridge columns or cover intervening prose."""
    unique = sorted({tuple(b) for b in boxes}, key=lambda b: (round(b[1], 2), b[0]))
    lines = []
    for box in unique:
        matched = None
        for line in reversed(lines):
            overlap = min(line[3], box[3]) - max(line[1], box[1])
            if overlap > min(line[3] - line[1], box[3] - box[1]) * 0.45 and (
                -0.004 <= box[0] - line[2] <= 0.025
            ):
                matched = line
                break
        if matched is None:
            lines.append(list(box))
        else:
            matched[:] = [
                min(matched[0], box[0]),
                min(matched[1], box[1]),
                max(matched[2], box[2]),
                max(matched[3], box[3]),
            ]
    return [[round(v, 6) for v in b] for b in lines]


def locate_span(page_text, start, end, mapping, index=None):
    if index:
        needle, _ = canonical(page_text[start:end])
        target, target_boxes, _ = index
        match = target.find(needle) if needle else -1
        # A rotated PDF can expose lines in a different native reading order.
        # A unique full-span match takes precedence over partial page alignment.
        if match >= 0 and target.find(needle, match + 1) < 0:
            boxes = [b for b in target_boxes[match : match + len(needle)] if b]
            coverage = len(boxes) / len(needle)
            if coverage >= 0.85:
                return merge_boxes(boxes), round(coverage, 3)
    expected = [i for i in range(start, end) if page_text[i].isalnum()]
    covered = [mapping[i] for i in expected if i in mapping]
    confidence = len(covered) / len(expected) if expected else 0
    # No invented page-sized rectangles when matching is uncertain.
    return (merge_boxes(covered) if confidence >= 0.85 else []), round(confidence, 3)


def search_boxes(data, number, page_text, query, words=None):
    needle, _ = canonical(query)
    text, offsets = canonical(page_text)
    if len(needle) < 2:
        return []
    index = page_index(data, number, words)
    mapping, _ = align_page(page_text, index)
    boxes, start = [], 0
    for _ in range(25):
        match = text.find(needle, start)
        if match < 0:
            break
        found, _ = locate_span(
            page_text, offsets[match], offsets[match + len(needle) - 1] + 1, mapping, index
        )
        boxes.extend(found)
        start = match + len(needle)
    return boxes


def render_page(data: bytes, number: int):
    with PDF_LOCK, pdfium.PdfDocument(data) as pdf:
        if not 1 <= number <= len(pdf):
            raise ValueError("PDF 페이지 범위를 벗어났습니다.")
        page = pdf[number - 1]
        try:
            width, height = page.get_size()
            scale = min(2.2, math.sqrt(12_000_000 / (width * height)))
            bitmap = page.render(scale=scale)
            try:
                with bitmap.to_pil() as image:
                    stream = BytesIO()
                    image.save(stream, format="PNG")
            finally:
                bitmap.close()
        finally:
            page.close()
    return {
        "image": "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode(),
        "width": width,
        "height": height,
    }


def attach_coordinates(model, result, assets):
    """Annotate only evidence pages. Full-document page images remain lazy."""
    documents = {d["document_id"]: d for d in result["documents"]}
    cache = {}
    for annotation in model["annotations"]:
        document = documents[annotation["document_id"]]
        page = document["pages"][annotation["page"] - 1]
        data = assets.get(document["document_id"])
        if data is None:
            annotation["location_method"] = "text"
            continue
        key = (document["document_id"], page["number"])
        if key not in cache:
            metadata = document.get("metadata", {})
            words = metadata.get("ocr_words", {})
            words = words.get(str(page["number"]), words.get(page["number"]))
            try:
                index = page_index(data, page["number"], words)
                cache[key] = (*align_page(page["text"], index), index)
            except (RuntimeError, ValueError, OSError):
                cache[key] = ({}, "unavailable", None)
        mapping, method, index = cache[key]
        boxes, coverage = locate_span(
            page["text"], annotation["start"], annotation["end"], mapping, index
        )
        annotation["boxes"] = boxes
        annotation["bbox"] = boxes[0] if boxes else None
        annotation["match_coverage"] = coverage
        annotation["location_method"] = method if boxes else "page_only"
    return model
