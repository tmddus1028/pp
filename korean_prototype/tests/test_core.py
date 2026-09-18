import io
from pathlib import Path
from xml.sax.saxutils import escape

import pytest
from pypdf import PdfWriter

from kr_review.ingestion import MAX_BYTES, MAX_XML_BYTES, evidence_at, read_document
from kr_review.models import ReviewError
from kr_review.parsers import claim_numbers, extract_claims
from kr_review.service import analyze

DATA = Path(__file__).resolve().parents[1] / "data" / "kr_1020190000844"


def oa_xml(claims="제1항", statute="특허법 제29조제2항", extra="", application="1020190000844"):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<krpat:PatentOpinionSubmission xmlns:krpat="urn:kr:gov:doc:kipo:patent"
 xmlns:krcom="urn:kr:gov:doc:kipo:common"
 xmlns:com="http://www.wipo.int/standards/XMLSchema/ST96/Common">
 <com:ApplicationNumberText>{application}</com:ApplicationNumberText>
 <krcom:SendDate>2019-04-09</krcom:SendDate>
 <krpat:ExaminationLawArticle><krcom:Row>
  <krcom:Entry>청구항 {claims}</krcom:Entry><krcom:Entry>{statute}</krcom:Entry>
 </krcom:Row></krpat:ExaminationLawArticle>
 <krpat:RejectionTitle>특허법 제63조에 따라 통지합니다.</krpat:RejectionTitle>
 <krpat:RejectionLawDetail><krcom:P>이 출원의 청구항 {claims}은 {statute}에 따라
 특허를 받을 수 없습니다.</krcom:P><krcom:P>{escape(extra)}</krcom:P></krpat:RejectionLawDetail>
 <krpat:GuidanceContent>청구항 제99항을 특허법 제47조제2항에 따라 보정하세요.
 인용발명 9 : 공개특허공보 제10-2010-0000001호</krpat:GuidanceContent>
</krpat:PatentOpinionSubmission>""".encode()


def patent_txt(claims):
    return (
        "출원번호 10-2019-0000844\n발명의 명칭 예시 장치\n청구범위\n"
        + "\n".join(f"청구항 {number}\n{text}" for number, text in claims)
        + "\n발명의 설명\n[0001] 이 장치에 관한 설명."
    ).encode()


def test_real_pair_with_all_prior_art_and_precise_evidence():
    result = analyze(
        (DATA / "KR20190025857A.pdf").read_bytes(),
        "KR20190025857A.pdf",
        (DATA / "office_action_20190409.xml").read_bytes(),
        "office_action_20190409.xml",
        [(path.name, path.read_bytes()) for path in DATA.glob("KR2015*.pdf")],
    )
    assert result.application_number == "1020190000844"
    assert result.title == "전자쿠폰 시스템 및 전자쿠폰 처리 방법"
    assert result.office_action_date == "2019-04-09"
    assert [claim.number for claim in result.claims] == [1]
    assert result.direct_claims == [1]
    assert result.dependency_claims == []
    assert len(result.rejections) == 1
    rejection = result.rejections[0]
    assert rejection.statute == "특허법 제29조제2항"
    assert rejection.claims == [1]
    assert set(rejection.citation_ids) == {"C1", "C2", "C3"}
    assert {citation.publication_number for citation in result.citations} == {
        "KR20150096573A",
        "KR20150090348A",
        "KR20150093093A",
    }
    assert all(citation.document_id for citation in result.citations)
    documents = {document.document_id: document for document in result.documents}
    evidence = [result.claims[0].evidence, rejection.evidence]
    evidence.extend(citation.evidence for citation in result.citations)
    for item in evidence:
        document = documents[item.document_id]
        assert document.text[item.start : item.end] == item.text
        assert item.page_numbers == [
            page.number
            for page in document.pages
            if page.start < item.end and item.start < page.end
        ]
    assert result.claims[0].evidence.page_numbers == [3]
    assert "발명의 설명" not in result.claims[0].text
    assert "장치 저장부" in result.claims[0].text
    assert "업체 정보 관리부" in result.claims[0].text
    assert rejection.evidence.page_numbers == []
    assert "RejectionLawDetail" in rejection.evidence.xml_path
    assert not any(
        "47조" in rejection.statute or "63조" in rejection.statute
        for rejection in result.rejections
    )


def test_transitive_and_alternative_dependencies_direct_wins():
    result = analyze(
        patent_txt(
            [
                (1, "검출부를 포함하는 장치."),
                (2, "제1항에 있어서, 통신부를 포함하는 장치."),
                (3, "제2항에 따른 장치."),
                (4, "제1항 내지 제3항 중 어느 한 항에 있어서, 기억부를 포함하는 장치."),
                (5, "삭제"),
                (6, "제1항 또는 제3항에 있어서, 저장부를 포함하는 장치."),
            ]
        ),
        "claims.txt",
        oa_xml("제1항 및 제3항"),
        "oa.xml",
    )
    assert result.direct_claims == [1, 3]
    assert result.dependency_claims == [2, 4, 6]
    assert result.claims[3].depends_on == [1, 2, 3]
    assert result.claims[4].status == "canceled"
    assert result.claims[5].depends_on == [1, 3]


@pytest.mark.parametrize(
    "value,expected",
    [
        ("제1항 내지 제3항 및 제8항", [1, 2, 3, 8]),
        ("청구항 제4항~제7항, 제9항, 제10항", [4, 5, 6, 7, 9, 10]),
        ("청구항 1-3, 8", [1, 2, 3, 8]),
    ],
)
def test_korean_claim_ranges(value, expected):
    assert claim_numbers(value) == expected


def test_prior_art_claim_numbers_and_guidance_never_become_subject_claims():
    extra = (
        "인용발명 1 : 공개특허공보 제10-2015-0096573호(2015.08.25.)\n"
        "인용발명 1의 청구항 4, 청구항 16, 청구항 99을 참조합니다.\n"
        "인용발명 1 : 공개특허공보 제10-2015-0096573호(2015.08.25.)\n"
        "단순 언급 공개특허공보 제10-2015-0090348호"
    )
    result = analyze(
        patent_txt([(1, "장치를 포함하는 시스템.")]), "p.txt", oa_xml(extra=extra), "oa.xml"
    )
    assert result.direct_claims == [1]
    assert len(result.rejections) == 1
    assert len(result.citations) == 1
    assert result.citations[0].publication_number == "KR20150096573A"


def test_registered_reference_does_not_get_invented_kind_code():
    result = analyze(
        patent_txt([(1, "장치를 포함하는 시스템.")]),
        "p.txt",
        oa_xml(extra="인용발명 1 : 등록특허공보 제10-1234567호"),
        "oa.xml",
    )
    assert result.citations[0].publication_number == "KR101234567"


def test_reference_link_uses_contents_not_misleading_filename():
    result = analyze(
        patent_txt([(1, "장치를 포함하는 시스템.")]),
        "p.txt",
        oa_xml(extra="인용발명 1 : 공개특허공보 제10-2015-0096573호"),
        "oa.xml",
        [("KR20150096573A.txt", "공개번호 10-2015-0090348\n다른 문서".encode())],
    )
    assert result.citations[0].document_id is None
    assert any("입력되지 않았습니다" in warning for warning in result.warnings)


def test_mismatched_application_rejected():
    with pytest.raises(ReviewError, match="출원번호가 다릅니다"):
        analyze(patent_txt([(1, "장치.")]), "p.txt", oa_xml(application="1020200000001"), "oa.xml")


def test_missing_application_warns_without_fabricating_match():
    data = "청구범위\n청구항 1\n장치.\n발명의 설명\n설명".encode()
    result = analyze(data, "p.txt", oa_xml(), "oa.xml")
    assert any("동일 출원 여부를 확인하지 못했습니다" in warning for warning in result.warnings)


@pytest.mark.parametrize(
    "claims,message",
    [
        ([(1, "제2항에 있어서 장치."), (2, "제1항에 있어서 장치.")], "순환"),
        ([(1, "제7항에 있어서 장치.")], "입력 문서에 없습니다"),
        ([(1, "삭제"), (2, "제1항에 있어서 장치.")], "삭제된 청구항"),
        ([(1, "장치."), (1, "다른 장치.")], "중복"),
    ],
)
def test_invalid_dependency_or_duplicate_rejected(claims, message):
    with pytest.raises(ReviewError, match=message):
        extract_claims(read_document(patent_txt(claims), "p.txt", "patent"))


def test_unknown_rejected_claim_fails_instead_of_false_success():
    with pytest.raises(ReviewError, match="입력 명세서에 없거나 삭제"):
        analyze(patent_txt([(1, "장치.")]), "p.txt", oa_xml("제9항"), "oa.xml")


@pytest.mark.parametrize(
    "declaration",
    [
        '<!DOCTYPE x [<!ENTITY a "text">]>',
        '<!DOCTYPE x SYSTEM "file:///C:/Windows/win.ini">',
    ],
)
def test_xml_entities_and_dtd_are_rejected(declaration):
    with pytest.raises(ReviewError, match="DTD"):
        read_document((declaration + "<x/>").encode(), "oa.xml", "office_action")


def test_wrong_or_broken_xml_rejected():
    with pytest.raises(ReviewError, match="형식이 올바르지"):
        read_document(b"<broken>", "oa.xml", "office_action")
    with pytest.raises(ReviewError, match="PatentOpinionSubmission"):
        read_document(b"<not_kipris/>", "oa.xml", "office_action")
    with pytest.raises(ReviewError, match="5 MB"):
        read_document(b" " * (MAX_XML_BYTES + 1), "oa.xml", "office_action")


def test_scanned_pdf_has_explicit_error_no_invented_text():
    writer = PdfWriter()
    writer.add_blank_page(width=600, height=800)
    stream = io.BytesIO()
    writer.write(stream)
    with pytest.raises(ReviewError, match="한국어 스캔 OCR"):
        read_document(stream.getvalue(), "scan.pdf", "patent")


def test_invalid_patent_and_oa_pdf_errors():
    with pytest.raises(ReviewError, match="PDF를 열거나"):
        read_document(b"not a PDF", "broken.pdf", "patent")
    with pytest.raises(ReviewError, match="PDF를 열거나"):
        read_document(b"pdf", "oa.pdf", "office_action")


def test_text_evidence_has_no_fabricated_page_and_checks_offsets():
    document = read_document(patent_txt([(1, "장치.")]), "p.txt", "patent")
    claim = extract_claims(document)[0]
    assert claim.evidence.page_numbers == []
    assert claim.evidence.text == document.text[claim.evidence.start : claim.evidence.end]
    with pytest.raises(ReviewError, match="문자 위치"):
        evidence_at(document, 5, 4)


def test_pdf_parser_fallback_reads_same_real_document(monkeypatch):
    import pypdf

    def fail(*args, **kwargs):
        raise ValueError("malformed page tree")

    monkeypatch.setattr(pypdf, "PdfReader", fail)
    document = read_document((DATA / "KR20190025857A.pdf").read_bytes(), "p.pdf", "patent")
    assert len(document.pages) == 17
    assert document.metadata["parser"] == "pdfium"
    assert [claim.number for claim in extract_claims(document)] == [1]


@pytest.mark.parametrize(
    "second_claim,second_law",
    [
        ("제2항", "특허법 제29조제2항"),
        ("제1항", "특허법 제42조제4항"),
    ],
)
def test_multiple_rejections_in_one_detail_fail_without_inventing_citation_relations(
    second_claim, second_law
):
    xml = oa_xml(extra=second_law + "에 해당합니다.").decode()
    xml = xml.replace(
        "</krpat:ExaminationLawArticle>",
        f"<krcom:Row><krcom:Entry>{second_claim}</krcom:Entry>"
        f"<krcom:Entry>{second_law}</krcom:Entry></krcom:Row></krpat:ExaminationLawArticle>",
    )
    with pytest.raises(ReviewError, match="하나의 거절이유 본문"):
        analyze(patent_txt([(1, "장치."), (2, "다른 장치.")]), "p.txt", xml.encode(), "oa.xml")


def test_core_input_limits_match_api():
    with pytest.raises(ReviewError, match="최대 10개"):
        analyze(b"", "p.txt", b"", "oa.xml", [("ref.txt", b"content")] * 11)
    with pytest.raises(ReviewError, match="20 MB"):
        read_document(b" " * (MAX_BYTES + 1), "p.txt", "patent")
