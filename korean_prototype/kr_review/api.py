from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import Field

from kr_review.models import AnalysisResult, Model, ReviewError
from kr_review.sample import sample_inputs

app = FastAPI(
    title="Patent Review · 한국어 프로토타입",
    description="기존 미국 버전과 분리된 한국 공개특허 PDF/TXT + 의견제출통지서 XML 분석 API",
    version="0.1.0",
)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


async def read_upload(upload: UploadFile) -> bytes:
    try:
        data = await upload.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await upload.close()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "파일당 최대 20 MB까지 입력할 수 있습니다.")
    if not data:
        raise HTTPException(422, "빈 파일은 입력할 수 없습니다.")
    return data


@app.get("/health")
def health():
    return {"status": "ok", "jurisdiction": "KR", "version": "0.1.0"}


@app.post("/demo/analyze", response_model=AnalysisResult)
def analyze_demo():
    from kr_review.service import analyze

    try:
        return analyze(**sample_inputs())
    except ReviewError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/analyze", response_model=AnalysisResult)
async def analyze_uploads(
    patent: Annotated[UploadFile, File(description="한국 공개특허 PDF 또는 UTF-8 TXT")],
    office_action: Annotated[UploadFile, File(description="KIPRIS 의견제출통지서 XML")],
    references: Annotated[list[UploadFile] | None, File()] = None,
):
    from kr_review.service import analyze

    if len(references or []) > 10:
        raise HTTPException(422, "인용발명은 최대 10개까지 입력할 수 있습니다.")
    patent_bytes = await read_upload(patent)
    oa_bytes = await read_upload(office_action)
    reference_bytes = [
        (f.filename or "reference.pdf", await read_upload(f)) for f in references or []
    ]
    try:
        return await run_in_threadpool(
            analyze,
            patent_bytes,
            patent.filename or "patent.pdf",
            oa_bytes,
            office_action.filename or "office_action.xml",
            reference_bytes,
        )
    except ReviewError as exc:
        raise HTTPException(422, str(exc)) from exc


class ReviewRequest(Model):
    analysis: AnalysisResult
    claim_number: int = Field(ge=1)


@app.post("/review")
def review_claim(request: ReviewRequest):
    from kr_review.review import analyze_with_azure

    try:
        return analyze_with_azure(request.analysis, request.claim_number)
    except ReviewError as exc:
        raise HTTPException(422, str(exc)) from exc
