from html.parser import HTMLParser

import pytest

from frontend.readable_text import text_html


class SourceTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_source = False
        self.source = []
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == "span" and dict(attrs).get("class") == "readable-text-content":
            self.in_source = True

    def handle_endtag(self, tag):
        if tag == "span":
            self.in_source = False

    def handle_data(self, data):
        if self.in_source:
            self.source.append(data)


@pytest.mark.parametrize(
    "text",
    [
        "Claims 1-4, 6, 8, 17-19 are rejected under 35 U.S.C. 103 as being "
        "unpatentable over Liu et al. in view of Donmez et al.",
        "Claims\n1-4,\n6,\n8,\n17-19\nare\nrejected\n\n35 U.S.C. §103\r\nUS 2023/0402512\tClaim 7",
        '<script>alert("source")</script>\n\nClaim < 20 & §112\n**literal** [source](url)',
    ],
)
def test_source_characters_survive_html_without_becoming_markup(text):
    parsed = SourceTextParser()
    parsed.feed(text_html(text, expandable=True))
    assert "".join(parsed.source) == text
    assert "script" not in parsed.tags
