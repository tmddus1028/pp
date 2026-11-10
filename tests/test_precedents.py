import json
from types import SimpleNamespace

import pytest
from conftest import ROOT
from fastapi.testclient import TestClient

from backend.analysis.checklist_generator import precedent_item
from backend.config import Settings
from backend.errors import ProviderError
from backend.improvements.models import ClaimImprovementSuggestion
from backend.improvements.providers import AnthropicImprovementProvider, get_provider
from backend.improvements.service import provider_settings, squash
from backend.main import app
from backend.precedents import repository
from backend.precedents.taxonomy import argument_types, categorize

DATA = ROOT / "data/precedents"


@pytest.mark.parametrize(
    "statute, jurisdiction, text, expected",
    [
        ("특허법 제29조제2항", "kr", "", "inventive_step"),
        ("특허법 제29조 제1항 제1호", "kr", "", "novelty"),
        ("특허법 제29조제1항 본문", "kr", "", "eligibility"),
        ("특허법 제29조제1항", "kr", "산업상 이용할 수 있는 발명이 아니므로", "eligibility"),
        ("특허법 제42조제4항제2호", "kr", "", "description"),
        ("특허법 제29조제3항", "kr", "", "prior_application"),
        ("특허법 제36조제1항", "kr", "", "prior_application"),
        ("35 U.S.C. 103", "us", "", "inventive_step"),
        ("35 U.S.C. § 102(a)(1)", "us", "", "novelty"),
        ("35 U.S.C. 112(b)", "us", "", "description"),
        ("103 - Obviousness", "us", "", "inventive_step"),
        ("Nonstatutory Double Patenting", "us", "", "prior_application"),
    ],
)
def test_common_rejection_mapping(statute, jurisdiction, text, expected):
    assert categorize(statute, jurisdiction, text) == expected


def test_argument_types():
    text = (
        "Applicant amends claim 1 by incorporating previous claims 6 and 35. Holt fails to "
        "teach the comparing step, and there is no motivation to combine Holt with Bureev. "
        "Support is found at paragraph [0084]."
    )
    found = argument_types(text)
    assert {"element_missing", "no_motivation", "dependent_merge", "limitation_added"} <= set(found)
    assert "teach_away" not in found


def test_korean_table_and_demo_cases_are_separate():
    cases = repository.load(repository.KR_PATH)
    assert len(cases) > 300 and len({c["case_id"] for c in cases}) == len(cases)
    for case in cases:
        assert case["jurisdiction"] == "KR" and not case.get("demo")
        assert case["outcome"] in {"resolved", "unresolved", "excluded"}
        if case["next_action"] == "등록결정":
            assert case["outcome"] in {"resolved", "excluded"}
    demo = repository.load(repository.DEMO_PATH)
    assert demo and all(c["demo"] and c["application"].startswith("DEMO-") for c in demo)
    # Demo cases never change the real statistics.
    real = repository.stats("inventive_step")
    assert real["labeled"] == sum(
        c["category"] == "inventive_step" and c["outcome"] != "excluded" for c in cases
    )


def test_similar_ranks_by_rejected_claim_words(monkeypatch):
    query = "소비자 단말 전자쿠폰 발급 승인 공급자 서버"
    found = repository.similar("inventive_step", query, 3, frozenset({"1020190000844"}))
    scores = [c["similarity"] for c in found]
    assert found and scores == sorted(scores, reverse=True)
    assert all(s >= repository.MIN_SIMILARITY and c["claims_before"] for s, c in zip(scores, found))
    assert repository.similar("inventive_step", "", 3) == []
    # With no real case above the floor, labelled demo cases stand in.
    monkeypatch.setattr(repository, "real_cases", lambda: ())
    demo = repository.similar("inventive_step", query, 3, frozenset({"1020190000844"}))
    assert demo and demo[0]["title"].startswith("전자쿠폰") and all(c["demo"] for c in demo)


def test_ipc_codes_from_publication_front_page():
    from korean_prototype.kr_review.ingestion import ipc_codes

    front = (
        "(51) 국제특허분류(Int. Cl.)\n     F01N 3/24 (2006.01)  B01D 53/94 (2006.01)\n"
        "     F01N 3/28 (2006.01)\n(21) 출원번호       10-2012-0152255\n"
    )
    assert ipc_codes(front) == ["F01N 3/24", "B01D 53/94", "F01N 3/28"]
    assert ipc_codes("청구항 1\nH01L 31/042 같은 문자열") == []  # only the (51) field counts


def test_similar_prefers_the_same_field(monkeypatch):
    def case(app, ipc, claim):
        return (
            {
                "case_id": app,
                "application": app,
                "category": "inventive_step",
                "outcome": "resolved",
                "claims_before": claim,
                "ipc": ipc,
            }
            | {k: "" for k in ("oa_type", "oa_date", "response_type", "next_action")}
            | {
                "argument_types": [],
                "examiner_reply": "unknown",
                "argument_excerpt": "",
                "examiner_reply_excerpt": "",
            }
        )

    claim = "단말기가 서버로 데이터를 전송하는 제어부와 통신부를 포함하는 시스템"
    pool = (
        case("telecom", ["H04W 72/04"], claim),
        case("coupon", ["G06Q 30/02"], "쿠폰을 발급하는 서버와 단말기의 표시부"),
        case("battery", ["H01M 10/05"], "양극 활물질과 전해질을 포함하는 이차전지"),
    )
    monkeypatch.setattr(repository, "real_cases", lambda: pool)
    query = claim + " 쿠폰"
    found = repository.similar("inventive_step", query, 5, frozenset(), ["G06Q 20/04"])
    # Same subclass is shown even with few shared words; a close other-field claim still shows,
    # an unrelated field does not.
    assert [c["application"] for c in found] == ["telecom", "coupon"] or [
        c["application"] for c in found
    ] == ["coupon", "telecom"]
    assert "battery" not in {c["application"] for c in found}
    without_ipc = repository.similar("inventive_step", query, 5, frozenset())
    assert [c["application"] for c in without_ipc] == ["telecom"]
    # Kiwi morphemes: particles do not split a word.
    assert "통신부" in repository.morphemes("통신부를") and "통신부" in repository.morphemes(
        "통신부가"
    )


def test_claim_history_is_merged_into_real_cases():
    if not repository.HISTORY_PATH.exists():
        pytest.skip("run scripts/build_kr_claim_history.py first")
    rounds = [c for c in repository.real_cases() if c["application"] == "1020190000844"]
    granted = next(c for c in rounds if c["next_action"] == "등록결정")
    # The re-examination amendment that led to grant: display resolution and NFC.
    assert "해상도" in granted["added_limitation"] and "NFC" in granted["added_limitation"]
    assert granted["amendment_documents"] and not granted.get("demo")
    # A real case finds real neighbours once their claims are comparable.
    case = next(c for c in repository.real_cases() if c.get("claims_before"))
    found = repository.similar(case["category"], case["claims_before"], 3)
    assert found and found[0]["case_id"] == case["case_id"]


def test_opinion_text_is_merged_into_real_cases():
    if not repository.OPINION_PATH.exists():
        pytest.skip("run scripts/build_kr_opinions.py first")
    rounds = [c for c in repository.real_cases() if c["application"] == "1020190000844"]
    by_date = {c["opinion_date"]: c for c in rounds if c.get("opinion_date")}
    # Each 의견서 lands on the round it answered: the first went to 거절결정, the second to 등록결정.
    assert by_date["2019-08-09"]["next_action"] == "거절결정"
    granted = by_date["2020-02-10"]
    assert granted["next_action"] == "등록결정" and "진보성" in granted["applicant_argument"]
    card = repository.summary(granted)
    assert card["applicant_argument"] and "opinion_text" not in card


@pytest.fixture
def tiny(tmp_path):
    base = {
        "application": "1",
        "round": 1,
        "oa_type": "Non-Final Rejection",
        "oa_date": "2023-01-01",
        "section_found": True,
        "examiner_reply": "unknown",
        "examiner_reply_excerpt": "",
        "category": "inventive_step",
        "exclusion_reason": None,
        "next_action": "Final Rejection",
    }
    rows = [
        {
            **base,
            "case_id": "A",
            "response_type": "amendment",
            "outcome": "resolved",
            "argument_types": ["dependent_merge"],
            "argument_excerpt": "wireless coupon beacon",
        },
        {
            **base,
            "case_id": "B",
            "response_type": "argument_only",
            "outcome": "resolved",
            "argument_types": ["element_missing"],
            "argument_excerpt": "gear housing",
        },
        {
            **base,
            "case_id": "C",
            "response_type": "amendment",
            "outcome": "unresolved",
            "argument_types": ["dependent_merge"],
            "argument_excerpt": "coupon issuing terminal",
        },
        {
            **base,
            "case_id": "D",
            "response_type": "amendment",
            "outcome": "excluded",
            "exclusion_reason": "rce",
            "argument_types": [],
            "argument_excerpt": "coupon",
        },
        {
            **base,
            "case_id": "E",
            "category": "novelty",
            "response_type": "amendment",
            "outcome": "resolved",
            "argument_types": [],
            "argument_excerpt": "x",
        },
    ]
    path = tmp_path / "cases.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return path


def test_stats_exclude_rce_and_split_response(tiny):
    stats = repository.stats("inventive_step", tiny)
    assert (stats["total"], stats["labeled"], stats["excluded"]) == (4, 3, 1)
    assert stats["resolved"] == 2 and stats["resolved_rate"] == pytest.approx(0.667)
    assert stats["by_response"]["amendment"] == {"cases": 2, "resolved": 1, "rate": 0.5}
    assert stats["by_response"]["argument_only"]["rate"] == 1.0


def test_find_mixes_outcomes_and_ranks_by_query(tiny):
    cases = repository.find("inventive_step", "coupon beacon", limit=3, path=tiny)
    assert [c["case_id"] for c in cases] == ["A", "B", "C"]
    assert all(c["case_id"] != "D" for c in cases)


def test_checklist_precedent_only_for_reusable_rejections(result):
    rejection = result.rejections[0].model_copy(update={"statute": "특허법 제29조제2항"})
    text, basis = precedent_item(rejection)
    assert "[대응 사례]" in text and "KIPRIS" in text and "미국" not in text
    assert basis["category"] == "inventive_step" and basis["cases"]
    eligibility = rejection.model_copy(update={"statute": "특허법 제29조제1항 본문"})
    assert precedent_item(eligibility) is None
    objection = rejection.model_copy(update={"action_type": "objection"})
    assert precedent_item(objection) is None


def test_precedent_api():
    client = TestClient(app)
    stats = client.get("/precedents/stats", params={"statute": "특허법 제29조제2항"}).json()
    assert stats["category"] == "inventive_step" and stats["labeled"] > 100
    found = client.get("/precedents", params={"category": "novelty", "limit": 2}).json()
    assert len(found) == 2
    assert client.get(f"/precedents/{found[0]['case_id']}").status_code == 200
    assert client.get("/precedents/nope").status_code == 404
    assert client.get("/precedents/stats").status_code == 422


def test_squash_tolerates_pdf_line_wraps():
    assert squash("고유 식별 코드를 부여하고") in squash("고유 식별 코드를 부\n여하고, 상기")


def suggestion():
    return ClaimImprovementSuggestion.model_validate(
        {
            "claim_number": 1,
            "jurisdiction": "kr",
            "issue_summary": "s",
            "rejection_basis": [],
            "element_comparison": [],
            "strategies": [],
            "optional_example": {
                "available": False,
                "text": None,
                "disclaimer": "d",
                "evidence_ids": [],
                "grounding": [],
            },
            "missing_evidence": [],
            "cautions": [],
        }
    )


class FakeMessages:
    def __init__(self, stop_reason="end_turn"):
        self.stop_reason, self.calls = stop_reason, []

    def stream(self, **kwargs):
        self.calls.append(kwargs)
        message = SimpleNamespace(stop_reason=self.stop_reason, parsed_output=suggestion())
        outer = self

        class Stream:
            def __enter__(self):
                return SimpleNamespace(get_final_message=lambda: message)

            def __exit__(self, *exc):
                return False

        del outer
        return Stream()


def test_anthropic_provider_structured_output():
    settings = Settings(_env_file=None, anthropic_model="claude-opus-5-5")
    messages = FakeMessages()
    provider = AnthropicImprovementProvider(settings, SimpleNamespace(messages=messages))
    draft = provider.generate_improvement({"jurisdiction": "kr", "claim_number": 1})
    assert draft.claim_number == 1
    call = messages.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["output_format"] is ClaimImprovementSuggestion
    assert "Jurisdiction KR" in call["system"] and "response_precedents" in call["system"]
    assert "thinking" not in call and "temperature" not in call


def test_anthropic_provider_rejects_incomplete_output():
    provider = AnthropicImprovementProvider(
        Settings(_env_file=None), SimpleNamespace(messages=FakeMessages("max_tokens"))
    )
    with pytest.raises(ProviderError):
        provider.generate_improvement({"jurisdiction": "kr", "claim_number": 1})


def test_kr_anthropic_never_falls_back_to_azure():
    settings = Settings(_env_file=None, improvement_provider="anthropic")
    config = provider_settings(settings, "kr")
    assert config.llm_provider == "anthropic"
    assert isinstance(get_provider(config), AnthropicImprovementProvider)


# --- KR (KIPRIS) -----------------------------------------------------------------------------

from backend.precedents.kipris import (  # noqa: E402
    Kipris,
    KiprisError,
    parse_items,
    publication_query,
)
from scripts.build_kr_precedents import build_app, decision_sections, rows  # noqa: E402

OA_TABLE = "순번†거절이유가 있는 부분†관련 법조항§1†청구항 제1항†특허법 제29조제2항§2†청구항 제2항†특허법 제42조제4항제2호"


def test_kipris_table_rows():
    assert rows(OA_TABLE) == [
        ("청구항 제1항", "특허법 제29조제2항"),
        ("청구항 제2항", "특허법 제42조제4항제2호"),
    ]
    assert rows("") == []


def test_decision_sections_per_reason_and_combined_layouts():
    per_reason = (
        "1. 이 출원은 아래와 같이 특허법 제42조제4항제1호에 따른 요건을 충족하지 못합니다.\n"
        "1-1. 의견 내용\n출원인은 실시예가 충분하다고 주장하였습니다.\n"
        "1-2. 의견 내용 검토\n일반화할 수 없습니다.\n"
        "2. 이 출원의 청구항 제1항은 특허법 제29조제2항에 따라 특허를 받을 수 없습니다.\n"
        "2-1. 의견 내용\n인용발명과 차이가 있다고 주장하였습니다.\n"
        "2-2. 의견 내용 검토\n쉽게 도출됩니다.\n<< 안내 >>\n"
    )
    found = decision_sections(per_reason)
    assert ("argument", "inventive_step", "인용발명과 차이가 있다고 주장하였습니다.") in found
    assert ("review", "description", "일반화할 수 없습니다.") in found
    combined = (
        "나. 거절이유 해소 여부\n※ 구성 대비는 “다. 의견서에 대한 검토”에 기재\n"
        "다. 의견서에 대한 검토\n출원인은 ①을 주장합니다. 살펴보면 공지입니다.\n"
    )
    roles = [(r, c) for r, c, _ in decision_sections(combined)]
    assert roles == [("review", None), ("argument", None), ("review", None)]


class FakeKipris:
    def __init__(self, data):
        self.data = data

    def items(self, service, operation, app):
        return self.data.get((service, operation), [])


def test_build_app_labels_from_refusal_table_and_flags_reexamination():
    a = "1020190000948"
    api = FakeKipris(
        {
            ("OP", "advancedSearchInfo"): [
                {"applicationNumber": a, "sendNumber": "1", "sendDate": "20190115"}
            ],
            ("OP", "examineResultInfo"): [
                {
                    "applicationNumber": a,
                    "sendNumber": "1",
                    "refusalLawTabularstatement": "h§1†청구항 제1항†특허법 제29조제1항제2호§2†청구항 제1항†특허법 제29조제2항",
                }
            ],
            ("RE", "advancedSearchInfo"): [
                {"applicationNumber": a, "sendNumber": "2", "sendDate": "20190705", "filePath": ""}
            ],
            ("RE", "examineResultInfo"): [
                {
                    "applicationNumber": a,
                    "sendNumber": "2",
                    "refusalLawTabularstatement": "h§1†청구항 제1항†특허법 제29조제2항",
                }
            ],
            ("RE", "rejectDecisionInfo"): [
                {
                    "applicationNumber": a,
                    "sendNumber": "2",
                    "lawContent": "의견서에 의하여 다시 심사",
                }
            ],
            ("RG", "bibliographicInfo"): [
                {"applicationNumber": a, "sendNumber": "3", "sendDate": "20191101"}
            ],
            ("RG", "contentInfo"): [
                {"applicationNumber": a, "sendNumber": "3", "content": "재심사 청구에 의하여"}
            ],
            ("CL", "amendmentHistoryInfo"): [
                {
                    "applicationNumber": a,
                    "receiptSendDate": "20190801",
                    "receiptSendDocumentName": "[명세서등 보정]보정서(재심사)",
                }
            ],
        }
    )
    refusals = []
    records = {(r["oa_type"], r["category"]): r for r in build_app(api, a, refusals)}
    [refusal] = refusals
    assert refusal["responded"] and refusal["has_unresolved_table"]
    novelty = records[("의견제출통지서", "novelty")]
    inventive = records[("의견제출통지서", "inventive_step")]
    assert (novelty["outcome"], inventive["outcome"]) == ("resolved", "unresolved")
    assert inventive["response_type"] == "argument_only"
    assert inventive["next_action"] == "거절결정"
    reexam = records[("거절결정서", "inventive_step")]
    assert reexam["outcome"] == "excluded" and reexam["exclusion_reason"] == "reexamination"
    assert reexam["next_action"] == "등록결정"


class FakeHttp:
    def __init__(self, text):
        self.text, self.calls = text, 0

    def get(self, url, params, timeout):
        self.calls += 1
        return SimpleNamespace(text=self.text, raise_for_status=lambda: None)


OK_XML = (
    "<response><header><resultCode></resultCode></header><body><items><advancedSearchInfo>"
    "<applicationNumber>1</applicationNumber><sendDate>20190101</sendDate>"
    "</advancedSearchInfo></items></body></response>"
)


def test_kipris_cache_and_monthly_guard(tmp_path, monkeypatch):
    http = FakeHttp(OK_XML)
    api = Kipris(key="k", cache=tmp_path, client=http, sleep=0)
    assert api.items("OP", "advancedSearchInfo", "1")[0]["sendDate"] == "20190101"
    api.items("OP", "advancedSearchInfo", "1")
    assert http.calls == 1  # second read served from disk
    monkeypatch.setattr("backend.precedents.kipris.MONTHLY_LIMIT", 1)
    with pytest.raises(KiprisError, match="한도"):
        api.items("OP", "advancedSearchInfo", "2")
    # Another teammate's key has its own monthly count.
    Kipris(key="other", cache=tmp_path, client=http, sleep=0).items("OP", "advancedSearchInfo", "2")
    expired = "<response><header><resultCode>31</resultCode><resultMsg>DEADLINE</resultMsg></header></response>"
    with pytest.raises(KiprisError, match="31"):
        parse_items(expired)


def test_quota_refusal_moves_to_the_next_key(tmp_path, monkeypatch):
    refused = (
        "<response><header><resultCode>22</resultCode><resultMsg>LIMITED</resultMsg>"
        "</header></response>"
    )

    class PerKeyHttp:
        def __init__(self):
            self.keys = []

        def get(self, url, params, timeout):
            self.keys.append(params["accessKey"])
            text = refused if params["accessKey"] == "mine" else OK_XML
            return SimpleNamespace(text=text, raise_for_status=lambda: None)

    monkeypatch.setattr("backend.precedents.kipris.access_keys", lambda: ["mine", "teammate"])
    http = PerKeyHttp()
    api = Kipris(cache=tmp_path, client=http, sleep=0)
    api.items("OP", "advancedSearchInfo", "1")
    api.items("OP", "advancedSearchInfo", "2")
    assert http.keys == ["mine", "teammate", "teammate"]  # a refused key is not retried


def test_publication_query_maps_citation_numbers():
    assert publication_query("KR20150090348A") == (
        {"openNumber": "1020150090348"},
        "getPubFullTextInfoSearch",
    )
    assert publication_query("KR102235736") == (
        {"registerNumber": "1022357360000"},
        "getAnnFullTextInfoSearch",
    )
    assert publication_query("KR102235736B1")[0] == {"registerNumber": "1022357360000"}
    assert publication_query("JP2009075123A") is None


class FakePublicationHttp:
    """KIPRIS 특허·실용 공개·등록공보: search → full-text path → PDF."""

    def __init__(self, pdf=b"%PDF-1.4 cited"):
        self.pdf, self.urls = pdf, []

    def get(self, url, params=None, timeout=None, follow_redirects=False):
        self.urls.append(url)
        if url.endswith("getAdvancedSearch"):
            text = (
                "<response><header><resultCode>00</resultCode></header><body><items><item>"
                "<applicationNumber>1020140010384</applicationNumber>"
                "<openNumber>1020150090348</openNumber></item></items></body></response>"
            )
        elif url.endswith("FullTextInfoSearch"):
            text = (
                "<response><header><resultCode>00</resultCode></header><body><item>"
                "<path>http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=a&amp;b=1</path>"
                "</item></body></response>"
            )
        else:
            return SimpleNamespace(content=self.pdf, raise_for_status=lambda: None)
        return SimpleNamespace(text=text, raise_for_status=lambda: None)


def test_cited_publication_pdf_is_fetched_once_and_cached(tmp_path):
    http = FakePublicationHttp()
    api = Kipris(key="k", cache=tmp_path, client=http, sleep=0)
    path = api.publication_pdf("KR20150090348A")
    assert path.read_bytes().startswith(b"%PDF")
    assert http.urls[-1].endswith("arg=a&b=1")  # XML-escaped download path
    assert api.publication_pdf("KR20150090348A") == path
    assert len(http.urls) == 3  # search, full text, download; second call from disk
    assert api.publication_pdf("JP2009075123A") is None


def test_failed_download_does_not_keep_the_tokened_path(tmp_path):
    api = Kipris(key="k", cache=tmp_path, client=FakePublicationHttp(b"<html>"), sleep=0)
    with pytest.raises(KiprisError, match="PDF"):
        api.publication_pdf("KR20150090348A")
    assert not list(tmp_path.glob("*/getPubFullTextInfoSearch/*.xml"))


def test_checklist_never_shows_the_analyzed_application_as_kr_precedent(result):
    rejection = result.rejections[0].model_copy(update={"statute": "특허법 제29조제2항"})
    _, basis = precedent_item(rejection)
    own = {c["application"] for c in basis["cases"]}
    assert own, "KIPRIS table should have inventive-step cases"
    _, filtered = precedent_item(rejection, frozenset(own))
    assert not {c["application"] for c in filtered["cases"]} & own
    assert filtered["stats"]["labeled"] < basis["stats"]["labeled"]


def test_no_response_refusal_is_excluded_not_unresolved():
    a = "1020140000601"
    api = FakeKipris(
        {
            ("OP", "advancedSearchInfo"): [
                {"applicationNumber": a, "sendNumber": "1", "sendDate": "20150910"}
            ],
            ("OP", "examineResultInfo"): [
                {
                    "applicationNumber": a,
                    "sendNumber": "1",
                    "refusalLawTabularstatement": "h§1†청구항 제1항†특허법 제29조제2항",
                }
            ],
            ("RE", "advancedSearchInfo"): [
                {"applicationNumber": a, "sendNumber": "2", "sendDate": "20151119", "filePath": ""}
            ],
            ("RE", "rejectDecisionInfo"): [
                {
                    "applicationNumber": a,
                    "sendNumber": "2",
                    "lawContent": "지정기간 2015.11.10.까지 의견서 또는 보정서 제출이 없었으며",
                }
            ],
        }
    )
    [record] = build_app(api, a)
    assert (record["outcome"], record["exclusion_reason"]) == ("excluded", "no_response")


def test_inline_argument_layout():
    from scripts.build_kr_precedents import inline_sections

    text = (
        "[거절결정의 이유]\n- 아 래 -\n  보정을 통하여 청구항 1을 감축하고, 동일자로 제출한\n"
        "의견서를 통하여 인용발명 1은 직접 접하는 구성이 아니라는 점을 근거로 진보성을 "
        "주장하였습니다.\n  먼저 살펴보면 인용발명 1에도 개시되어 있습니다.\n<< 안내 >>"
    )
    [(role, _, argument), (review_role, _, review)] = inline_sections(text)
    assert role == "argument" and "직접 접하는 구성이 아니라는 점" in argument
    assert review_role == "review" and review.startswith("먼저 살펴보면")


def test_ollama_grammar_schema_drops_upper_bounds_only():
    from backend.improvements.providers import grammar_schema

    schema = grammar_schema(ClaimImprovementSuggestion.model_json_schema())
    text = json.dumps(schema)
    assert "maxLength" not in text and "maxItems" not in text
    assert "minLength" in text and "minItems" in text
    with pytest.raises(ValueError):
        ClaimImprovementSuggestion.model_validate(
            suggestion().model_dump() | {"strategies": [{}] * 9}
        )


def test_google_patents_fallback_for_cited_publications(tmp_path):
    from backend.precedents.kipris import google_publication_pdf

    class FakeGoogle:
        def __init__(self):
            self.urls = []

        def get(self, url, headers, timeout):
            self.urls.append(url)
            if url.endswith(".pdf"):
                return SimpleNamespace(status_code=200, content=b"%PDF-1.4 x")
            found = "B1" in url
            text = 'href="https://patentimages.storage.googleapis.com/a/KR1.pdf"' if found else ""
            return SimpleNamespace(status_code=200 if found else 404, text=text)

    http = FakeGoogle()
    path = google_publication_pdf("KR102235736", cache=tmp_path, client=http)
    assert path.read_bytes().startswith(b"%PDF")
    assert http.urls[0].endswith("/KR102235736B1/ko")  # registered number gets its kind code
    assert google_publication_pdf("KR102235736", cache=tmp_path, client=None) == path  # cached
    with pytest.raises(KiprisError, match="Google"):
        google_publication_pdf("KR20150000001A", cache=tmp_path, client=FakeGoogle())
