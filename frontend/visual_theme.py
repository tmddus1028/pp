"""Decorative markup only; no widgets, events, document data or session state."""

from html import escape

BRAND_HTML = """<div class="brand"><svg class="patent-brand-mark" aria-hidden="true" viewBox="0 0 64 70" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 18h44M14 11h36L32 6 14 11ZM13 62h38M10 66h44M24 26v34m8-34v34m8-34v34M20 25c-9 9-15-7-5-7h34c10 0 4 16-5 7M18 24c-3-3-6 1-3 3m31-3c3-3 6 1 3 3"/></svg><span class="brand-name">Patent Review</span></div>"""

HERO_DECORATION = """<div class="patent-hero-art" aria-hidden="true"><svg viewBox="0 0 450 225" fill="none" xmlns="http://www.w3.org/2000/svg" focusable="false"><g class="patent-paper-art" stroke="currentColor" stroke-width=".9" transform="translate(20 28) rotate(-6 110 100)"><rect width="220" height="208"/><rect x="11" y="11" width="198" height="186"/><text x="110" y="46" text-anchor="middle" fill="currentColor" stroke="none" font-family="Georgia,serif" font-size="13" letter-spacing="2">INTELLECTUAL</text><text x="110" y="65" text-anchor="middle" fill="currentColor" stroke="none" font-family="Georgia,serif" font-size="13" letter-spacing="2">PROPERTY</text><g stroke-width=".7"><path d="M35 91h146M35 97h146M35 103h128M35 116h146M35 122h146M35 128h133M35 141h146M35 147h146M35 153h117M35 170h58M35 176h87"/></g></g><g class="patent-blueprint-art" transform="translate(259 8)" stroke="currentColor" stroke-width=".8"><path d="M3 13h143v175H3z" stroke-dasharray="2 4"/><path d="M73-7v192M-12 96h179M-4 25h153M-4 164h153" stroke-dasharray="7 3 1 3"/><circle cx="73" cy="96" r="43"/><circle cx="73" cy="96" r="31"/><circle cx="73" cy="96" r="23"/><path d="M61 52V34l-6-5 10-6 3-19 5-4 5 4 3 19 10 6-6 5v18M46 62l7 8m40 52 8 8M101 62l-8 8m-40 52-7 8M65 138v13h16v-13M30 91H17v10h13m86-10h13v10h-13"/><path d="M132 35v116m-4-116h8m-8 116h8M17 178h112m-112-4v8m112-8v8M17 106v77m112-77v77M87 35h53M81 151h59" stroke-width=".6"/><g fill="currentColor" stroke="none" font-family="Georgia,serif" font-size="8"><text x="137" y="99" transform="rotate(-90 137 99)">124</text><text x="68" y="175">86</text><text x="8" y="201" font-size="10" letter-spacing="1">FIG. 1</text></g></g></svg><span class="patent-editorial">PATENTS<br>DRIVE<br>A BETTER<br>TOMORROW</span></div>"""


def upload_header(label, subtitle):
    """Shared number/title/subtitle/icon grid; native heading keeps its accessible name."""
    number, title = label.split(" · ", 1)
    drawing = (
        '<path d="M5 55V5h28M10 61V10h24l12 12v39H10zM34 10v13h12M17 30h21M17 37h21M17 44h21M17 51h13"/>'
        if number == "01"
        else '<path d="M7 60V5h25l14 14v22M32 5v15h14M14 28h24M14 35h24M14 42h14M14 49h9M7 60h18"/><path d="M38 43c-10 0-16 5-16 11 0 4 3 7 8 9v7l8-6c10 0 16-4 16-10s-6-11-16-11Z"/>'
    )
    caption = "SPECIFICATION<br>&amp; CLAIMS" if number == "01" else "OFFICE ACTION<br>RESPONSE"
    return (
        f'<div class="patent-upload-heading" aria-hidden="true"><span class="patent-step">{escape(number)}</span>'
        '<span class="upload-title-group">'
        f'<span class="upload-card-title">{escape(title)}</span>'
        f'<span class="upload-card-subtitle">{escape(subtitle)}</span></span>'
        '<span class="upload-icon-slot"><span class="upload-icon-detail">'
        '<svg class="patent-document-mark" aria-hidden="true" focusable="false" viewBox="0 0 60 74" '
        'fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round">'
        f'{drawing}</svg><span class="patent-detail-caption">{caption}</span>'
        "</span></span></div>"
    )
