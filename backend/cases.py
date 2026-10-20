"""Saved cases for the web client.

Lives outside main.py so parallel backend work merges cleanly; main.py only includes the router.
Imported by main.py at its end, so always import the app via backend.main.
"""

import hashlib
from datetime import date
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import quote

import psycopg
from fastapi import APIRouter, Form, HTTPException, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend import store
from backend.errors import ProviderError
from backend.improvements.opinion import Selection, check_selection, generate_from_selection
from backend.main import Config, analyze_files, analyze_text, app
from backend.schemas import AnalysisResult, TextAnalysisRequest
from backend.view.models import build_relationship_model, claim_rows, comparison_for_claim
from backend.view.pdf_adapter import attach_coordinates, render_png, search_boxes
from backend.view.review_model import build_review_model
from backend.view.terminology import component_terms

ROOT = Path(__file__).resolve().parents[1]
router = APIRouter(prefix="/cases", tags=["cases"])
Status = Literal["open", "in_progress", "responded", "closed"]


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    status: Status | None = None
    deadline: date | None = None


@app.exception_handler(psycopg.OperationalError)
def database_unavailable(_request: Request, _exc: psycopg.OperationalError):
    return JSONResponse(
        status_code=503,
        content={
            "detail": "DB에 연결할 수 없습니다. docker compose up -d 로 PostgreSQL을 실행하세요."
        },
    )


def save(result: AnalysisResult, uploads, title):
    """Persist the analysis, its PDFs and the coordinate-resolved review model once."""
    data = result.model_dump(mode="json")
    # Same PDF↔document matching the Streamlit upload used (KR ids end with the file hash).
    files = {
        document["document_id"]: (name, content)
        for document in data["documents"]
        for name, content in uploads
        if Path(name).suffix.lower() == ".pdf"
        and document["filename"] == name
        and document["document_id"].endswith(hashlib.sha256(content).hexdigest()[:16])
    }
    assets = {document_id: content for document_id, (_, content) in files.items()}
    review = attach_coordinates(build_review_model(data), data, assets)
    case_id = store.create_case(data["analysis_id"], title, "KR", data, review, files)
    return {"id": case_id}


# The web product handles Korean 의견제출통지서 only.
@router.post("", status_code=201)
async def create_case(
    patent: UploadFile,
    office_action: UploadFile,
    settings: Config,
    references: list[UploadFile] | None = None,
    amendments: list[UploadFile] | None = None,
    version_history: Annotated[str | None, Form(max_length=20000)] = None,
    title: Annotated[str | None, Form(max_length=200)] = None,
):
    limit = settings.max_upload_mb * 1024 * 1024 + 1
    uploads = []
    for upload in [patent, office_action, *(references or [])]:
        uploads.append((upload.filename or "upload", await upload.read(limit)))
        await upload.seek(0)  # analyze_files re-reads and enforces the size limits
    result = await analyze_files(
        patent, office_action, settings, "KR", references, amendments, version_history
    )
    name = title or Path(patent.filename or "사건").stem
    return await run_in_threadpool(save, result, uploads, name)


@router.post("/text", status_code=201)
def create_text_case(request: TextAnalysisRequest, settings: Config):
    result = analyze_text(request, settings, "KR")
    return save(result, [], "텍스트 입력 · " + date.today().isoformat())


@router.post("/demo", status_code=201)
def create_demo_case(settings: Config):
    raw = ROOT / "data/raw"
    request = TextAnalysisRequest(
        patent_text=(raw / "kr_demo_patent.txt").read_text(encoding="utf-8"),
        office_action_text=(raw / "kr_demo_office_action.xml").read_text(encoding="utf-8"),
    )
    result = analyze_text(request, settings, "KR")
    return save(result, [], "예제 분석 · 가상 문서")


@router.get("")
def list_cases():
    return store.list_cases()


def load(case_id):
    case = store.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="사건을 찾을 수 없습니다.")
    return case


@router.get("/{case_id}")
def get_case(case_id: int):
    case = load(case_id)
    result, review = case.pop("result"), case.pop("review")
    return {
        "case": case,
        "result": result,
        "review": review,
        "relationship": build_relationship_model(result),
        "claim_rows": claim_rows(result)[0],
        "terms": component_terms(result),
    }


@router.patch("/{case_id}")
def update_case(case_id: int, update: CaseUpdate):
    # null clears the deadline; null title/status would break NOT NULL, so ignore them.
    fields = {
        key: value
        for key, value in update.model_dump(exclude_unset=True).items()
        if value is not None or key == "deadline"
    }
    case = store.update_case(case_id, fields)
    if case is None:
        raise HTTPException(status_code=404, detail="사건을 찾을 수 없습니다.")
    return case


@router.delete("/{case_id}", status_code=204)
def delete_case(case_id: int):
    if not store.delete_case(case_id):
        raise HTTPException(status_code=404, detail="사건을 찾을 수 없습니다.")


@router.get("/{case_id}/comparison")
def comparison(case_id: int, claim: int, scope: str = "all"):
    review = load(case_id)["review"]
    if not any(item.get("claim_number") == claim for item in review["items"]):
        raise HTTPException(status_code=404, detail="청구항을 찾을 수 없습니다.")
    return comparison_for_claim(review, claim, scope)


@router.get("/{case_id}/selections")
def list_selections(case_id: int):
    """Every confirmed version, newest first per issue (요구사항 5장 선택 확정 기록)."""
    load(case_id)
    return store.list_selections(case_id)


@router.post("/{case_id}/selections", status_code=201)
def confirm_selection(case_id: int, selection: Selection):
    result = AnalysisResult.model_validate(load(case_id)["result"])
    try:
        check_selection(selection, result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    record = selection.model_dump(mode="json", exclude={"confirmed_by"})
    return store.create_selection(case_id, selection.rejection_id, record, selection.confirmed_by)


class DraftRequest(BaseModel):
    selection_id: int


@router.post("/{case_id}/drafts", status_code=201)
def create_draft(case_id: int, request: DraftRequest, settings: Config):
    """Draft from one confirmed selection version; the record keeps what it was written from."""
    result = AnalysisResult.model_validate(load(case_id)["result"])
    saved = store.get_selection(case_id, request.selection_id)
    if saved is None:
        raise HTTPException(status_code=404, detail="선택 기록을 찾을 수 없습니다.")
    selection = Selection(**saved["record"], confirmed_by=saved["confirmed_by"])
    try:
        response, model = generate_from_selection(result, selection, settings)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return store.create_draft(
        case_id, saved["id"], response.provider, model, response.model_dump(mode="json")
    )


@router.get("/{case_id}/drafts")
def list_drafts(case_id: int):
    load(case_id)
    return store.list_drafts(case_id)


def case_file(case_id, document_id):
    file = store.get_file(case_id, document_id)
    if file is None:
        raise HTTPException(status_code=404, detail="원본 PDF가 없습니다.")
    return file


@router.get("/{case_id}/files/{document_id}", response_class=Response)
def download_file(case_id: int, document_id: str):
    file = case_file(case_id, document_id)
    return Response(
        file["data"],
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename*=UTF-8''" + quote(file["filename"])},
    )


@router.get("/{case_id}/files/{document_id}/pages/{number}", response_class=Response)
def page_image(case_id: int, document_id: str, number: int):
    try:
        png, _, _ = render_png(case_file(case_id, document_id)["data"], number)
    except (RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail=f"PDF 페이지 렌더링 실패: {exc}") from exc
    # A saved case's files never change, so the browser may keep each page.
    return Response(
        png,
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )


@router.get("/{case_id}/files/{document_id}/pages/{number}/search")
def search_page(case_id: int, document_id: str, number: int, q: str):
    document = next(
        (d for d in load(case_id)["result"]["documents"] if d["document_id"] == document_id), None
    )
    if document is None or not 1 <= number <= len(document["pages"]):
        raise HTTPException(status_code=404, detail="페이지를 찾을 수 없습니다.")
    words = document.get("metadata", {}).get("ocr_words", {})
    words = words.get(str(number), words.get(number))
    try:
        return search_boxes(
            case_file(case_id, document_id)["data"],
            number,
            document["pages"][number - 1]["text"],
            q[:300],
            words,
        )
    except (RuntimeError, ValueError, OSError):
        return []
