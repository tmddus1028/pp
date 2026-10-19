"""KIPRIS Plus REST client for KR prosecution outcomes (OA → response → decision).

Services this team subscribed to (free, 1,000 calls/month each, until 2026-12-31):
- IntermediateDocumentOPService  의견제출통지서
- IntermediateDocumentREService  거절결정서
- IntermediateDocumentRGService  등록결정서
- ClaimsChangeHistoryService     청구항 변동 이력
Operation names come from each service's spec page (plus.kipris.or.kr/portal/popup/service/
DBII_000000000000242|243|317|327/view.do).

Every response is cached on disk, so rebuilding never spends quota twice, and a per-service
monthly counter stops before the free limit.
"""

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


class KiprisError(RuntimeError):
    pass


def access_key():
    env = dotenv_values(ROOT / ".env")
    for name in KEY_NAMES:
        value = (os.environ.get(name) or env.get(name) or "").strip()
        if value:
            return value
    raise KiprisError(".env에 KIPRIS_ACCESS_KEY(또는 REST_AccessKey)를 설정하세요.")


def clean(text):
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

    def _usage(self):
        try:
            return json.loads(self.usage_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _count(self, service):
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

    def raw(self, service, operation, application_number):
        name = SERVICES.get(service, service)
        path = self.cache / name / operation / f"{application_number}.xml"
        if path.exists():
            return path.read_text(encoding="utf-8")
        self._count(name)
        response = self._get(
            f"{BASE}/{name}/{operation}",
            {"applicationNumber": application_number, "accessKey": self.key or access_key()},
        )
        text = response.text
        parse_items(text)  # raise on API errors before caching
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        time.sleep(self.sleep)
        return text

    def search_by_date(self, send_date, start=1, count=50):
        """의견제출통지서 발송일 검색 → (applicationNumber list, total). Cached like other calls."""
        name = SERVICES["OP"]
        path = self.cache / name / "advancedSearchInfo-date" / f"{send_date}-{start}-{count}.xml"
        if not path.exists():
            self._count(name)
            response = self._get(
                f"{BASE}/{name}/advancedSearchInfo",
                {
                    "sendDate": send_date,
                    "docsStart": start,
                    "docsCount": count,
                    "accessKey": self.key or access_key(),
                },
            )
            parse_items(response.text)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(response.text, encoding="utf-8")
            time.sleep(self.sleep)
        text = path.read_text(encoding="utf-8")
        total = re.search(r"<totCnt>(\d+)</totCnt>", text)
        return [i["applicationNumber"] for i in parse_items(text)], int(
            total.group(1)
        ) if total else 0

    def items(self, service, operation, application_number):
        return parse_items(self.raw(service, operation, application_number))

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
