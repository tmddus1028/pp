"""KIPRIS Plus REST client for KR prosecution outcomes (OA → response → decision).

Services this team subscribed to (free, 1,000 calls/month each, until 2026-12-31):
- IntermediateDocumentOPService  의견제출통지서
- IntermediateDocumentREService  거절결정서
- IntermediateDocumentRGService  등록결정서
- ClaimsChangeHistoryService     청구항 변동 이력
Operation names come from each service's spec page (plus.kipris.or.kr/portal/popup/service/
DBII_000000000000242|243|317|327/view.do).
- patUtiModInfoSearchSevice      특허·실용 공개·등록공보 (cited publications' full-text PDF;
                                 kipo-api path with ServiceKey, same key)

Every response is cached on disk, so rebuilding never spends quota twice, and a per-service
monthly counter stops before the free limit.
"""

import hashlib
import html
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
BASE = "http://plus.kipris.or.kr/openapi/rest"
CACHE = ROOT / "data/kipris_cache"
MONTHLY_LIMIT = 950  # free tier is 1,000 per service; keep headroom for manual checks
KEY_NAMES = ("KIPRIS_ACCESS_KEY", "REST_AccessKey")

SERVICES = {
    "OP": "IntermediateDocumentOPService",
    "RE": "IntermediateDocumentREService",
    "RG": "IntermediateDocumentRGService",
    "CL": "ClaimsChangeHistoryService",
}
PUBLICATION_BASE = "http://plus.kipris.or.kr/kipo-api/kipi"
PUBLICATION_SERVICE = "patUtiModInfoSearchSevice"  # KIPRIS's own spelling


def publication_query(publication):
    """KR citation number (oa.canonical_publication form) → search params and full-text operation.

    KR20150090348A → 공개 10-2015-0090348; KR102235736[B1] → 등록 10-2235736 (KIPRIS pads to 13).
    """
    m = re.fullmatch(r"KR(\d{4})(\d{7})A\d?", publication)
    if m:
        return {"openNumber": f"10{m[1]}{m[2]}"}, "getPubFullTextInfoSearch"
    m = re.fullmatch(r"KR10(\d{7})(?:B\d?)?", publication)
    if m:
        return {"registerNumber": f"10{m[1]}0000"}, "getAnnFullTextInfoSearch"
    return None


def publication_pdf_path(publication, cache=CACHE):
    """Where publication_pdf keeps a cited publication's PDF."""
    return Path(cache) / "pdf" / f"{publication}.pdf"


class KiprisError(RuntimeError):
    pass


GOOGLE_PATENTS = "https://patents.google.com/patent/{}/ko"
GOOGLE_UA = {"User-Agent": "Mozilla/5.0 (PinPoint research)"}


def google_publication_pdf(publication, cache=CACHE, client=None):
    """The same KR publication PDF from Google Patents, when KIPRIS is out of quota or the key
    is not subscribed to 공보. Cached at publication_pdf_path like the KIPRIS copy."""
    path = publication_pdf_path(publication, cache)
    if path.exists():
        return path
    client = client or httpx
    # A registered number ("KR10" + 7 digits) has no kind code; Google wants B1 or B.
    registered = re.fullmatch(r"KR10\d{7}", publication)
    names = [publication + "B1", publication + "B"] if registered else [publication]
    for name in names:
        try:
            page = client.get(GOOGLE_PATENTS.format(name), headers=GOOGLE_UA, timeout=30)
            url = re.search(r"https://patentimages[^\"]+\.pdf", page.text)
            if page.status_code != 200 or not url:
                continue
            pdf = client.get(url[0], headers=GOOGLE_UA, timeout=60)
        except httpx.HTTPError:
            continue
        if pdf.content.startswith(b"%PDF"):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(pdf.content)
            return path
    raise KiprisError(f"{publication} 원문을 KIPRIS·Google Patents에서 받지 못했습니다.")


def access_keys():
    """KIPRIS keys from the environment or .env: KIPRIS_ACCESS_KEY, REST_AccessKey, then
    teammates' KIPRIS_ACCESS_KEY_2, _3, … (used in order when the one before runs out)."""
    env = {**dotenv_values(ROOT / ".env"), **os.environ}
    extra = sorted(
        (n for n in env if re.fullmatch(r"KIPRIS_ACCESS_KEY_\d+", n)),
        key=lambda n: int(n.rsplit("_", 1)[1]),
    )
    keys = [(env.get(n) or "").strip() for n in (*KEY_NAMES, *extra)]
    keys = list(dict.fromkeys(k for k in keys if k))
    if not keys:
        raise KiprisError(".env에 KIPRIS_ACCESS_KEY(또는 REST_AccessKey)를 설정하세요.")
    return keys


def access_key():
    return access_keys()[0]


def clean(text):
    """Unescape KIPRIS text and turn <br> into newlines."""
    text = html.unescape(text or "")
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.I)
    return re.sub(r"[ \t]+", " ", text).strip()


def parse_items(xml_text):
    """Each leaf-parent element under <items> becomes a dict of its child tags."""
    root = ET.fromstring(xml_text)
    code = (root.findtext("header/resultCode") or "").strip()
    message = (root.findtext("header/resultMsg") or "").strip()
    if code not in {"", "00"}:
        raise KiprisError(f"KIPRIS 오류 {code}: {message}")
    items = []
    for element in root.iter():
        children = list(element)
        if children and all(len(c) == 0 for c in children) and element.tag not in {"header"}:
            if element.find("applicationNumber") is not None:
                items.append({c.tag: clean(c.text) for c in children})
    return items


class Kipris:
    def __init__(self, key=None, cache=CACHE, client=None, sleep=0.3):
        self.key = key
        self.cache = Path(cache)
        self.client = client
        self.sleep = sleep
        self.cache.mkdir(parents=True, exist_ok=True)
        self.usage_path = self.cache / "usage.json"
        self.exhausted = set()  # keys refused this run (our guard or KIPRIS 오류 22)

    def _usage(self):
        try:
            return json.loads(self.usage_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _count(self, service, key):
        # Counted per key (a short hash, never the key): a teammate's key has its own quota.
        service = f"{service} #{hashlib.sha256(key.encode()).hexdigest()[:6]}"
        usage = self._usage()
        month = date.today().strftime("%Y-%m")
        used = usage.setdefault(month, {}).get(service, 0)
        if used >= MONTHLY_LIMIT:
            raise KiprisError(f"{service} 이번 달 호출 {used}회: 무료 한도 보호로 중단합니다.")
        usage[month][service] = used + 1
        self.usage_path.write_text(json.dumps(usage, indent=2) + "\n", encoding="utf-8")

    def _get(self, url, params, attempts=3):
        """KIPRIS sometimes resets connections; retry with backoff before giving up."""
        client = self.client or httpx
        for attempt in range(attempts):
            try:
                response = client.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response
            except httpx.HTTPError as exc:
                if attempt + 1 == attempts:
                    raise KiprisError(f"KIPRIS 연결 실패: {exc}") from exc
                time.sleep(2 * (attempt + 1))

    def _fetch(self, service, url, params, key_param="accessKey"):
        """GET with the first key that still has quota; a quota refusal moves to the next key."""
        error = None
        for key in [self.key] if self.key else access_keys():
            if key in self.exhausted:
                continue
            try:
                self._count(service, key)
                text = self._get(url, params | {key_param: key}).text
                parse_items(text)  # raise on API errors before caching
                return text
            except KiprisError as exc:
                # 22 = quota used up, 31 = this key's subscription to the service expired/absent.
                if not re.search(r"한도|오류 (?:22|31)", str(exc)):
                    raise
                self.exhausted.add(key)
                error = exc
        raise error or KiprisError(f"{service}: 남은 KIPRIS 키가 없습니다 (모두 한도).")

    def raw(self, service, operation, application_number):
        name = SERVICES.get(service, service)
        path = self.cache / name / operation / f"{application_number}.xml"
        if path.exists():
            return path.read_text(encoding="utf-8")
        text = self._fetch(
            name, f"{BASE}/{name}/{operation}", {"applicationNumber": application_number}
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        time.sleep(self.sleep)
        return text

    def search_by_date(self, send_date, start=1, count=50):
        """의견제출통지서 발송일 검색 → (applicationNumber list, total). Cached like other calls."""
        name = SERVICES["OP"]
        path = self.cache / name / "advancedSearchInfo-date" / f"{send_date}-{start}-{count}.xml"
        if not path.exists():
            text = self._fetch(
                name,
                f"{BASE}/{name}/advancedSearchInfo",
                {"sendDate": send_date, "docsStart": start, "docsCount": count},
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            time.sleep(self.sleep)
        text = path.read_text(encoding="utf-8")
        total = re.search(r"<totCnt>(\d+)</totCnt>", text)
        return [i["applicationNumber"] for i in parse_items(text)], int(
            total.group(1)
        ) if total else 0

    def items(self, service, operation, application_number):
        """Parsed rows of service/operation for one application number (cached)."""
        return parse_items(self.raw(service, operation, application_number))

    def _publication(self, operation, params, name):
        """One cached patUtiModInfoSearchSevice call."""
        path = self.cache / PUBLICATION_SERVICE / operation / f"{name}.xml"
        if path.exists():
            return path.read_text(encoding="utf-8")
        text = self._fetch(
            PUBLICATION_SERVICE,
            f"{PUBLICATION_BASE}/{PUBLICATION_SERVICE}/{operation}",
            params,
            "ServiceKey",
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        time.sleep(self.sleep)
        return text

    def publication_pdf(self, publication):
        """Full-text PDF of a cited KR publication (cached), or None for non-KR numbers."""
        query = publication_query(publication)
        if query is None:
            return None
        path = publication_pdf_path(publication, self.cache)
        if path.exists():
            return path
        params, fulltext = query
        found = parse_items(self._publication("getAdvancedSearch", params, publication))
        ((field, number),) = params.items()
        found = [i for i in found if i.get(field) == number] or found
        if not found:
            raise KiprisError(f"{publication}을 KIPRIS에서 찾지 못했습니다.")
        application = found[0]["applicationNumber"]
        text = self._publication(fulltext, {"applicationNumber": application}, application)
        url = re.search(r"<path>([^<]+)</path>", text)
        if not url:
            raise KiprisError(f"{publication}의 전문 PDF가 KIPRIS에 없습니다.")
        try:
            return self.document_pdf(html.unescape(url[1]), publication)
        except KiprisError:
            # The path carries a download token; ask for a fresh one next time.
            (self.cache / PUBLICATION_SERVICE / fulltext / f"{application}.xml").unlink(
                missing_ok=True
            )
            raise

    def document_pdf(self, url, name):
        """PDF behind an advancedSearchInfo filePath (cached; not counted as an API call)."""
        path = self.cache / "pdf" / f"{name}.pdf"
        if not path.exists():
            client = self.client or httpx
            try:
                response = client.get(url, timeout=60, follow_redirects=True)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise KiprisError(f"KIPRIS 문서 다운로드 실패: {exc}") from exc
            if not response.content.startswith(b"%PDF"):
                raise KiprisError("KIPRIS 문서 응답이 PDF가 아닙니다.")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(response.content)
        return path
