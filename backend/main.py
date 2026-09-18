import json
from functools import lru_cache
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from backend.config import Settings
from backend.errors import DocumentError, ExtractionError, ProviderError
from backend.ingestion.adapters import LocalAdapter, from_text
from backend.schemas import AnalysisResult, TextAnalysisRequest
from backend.service import analyze

app = FastAPI(
    title="Patent Review API",
    version="0.1.0",
    description="Evidence-linked patent analysis. Does not provide legal advice.",
)


@lru_cache
def get_settings() -> Settings:
    return Settings()


Config = Annotated[Settings, Depends(get_settings)]
Jurisdiction = Literal["US", "KR", "us", "kr"]


from backend.improvements.models import ImprovementRequest, ImprovementResponse  # noqa: E402
from backend.improvements.revision import review_revision  # noqa: E402
from backend.improvements.revision_models import RevisionRequest, RevisionReview  # noqa: E402
from backend.improvements.service import generate_improvement  # noqa: E402


@app.post("/improvements", response_model=ImprovementResponse)
def improvements(request: ImprovementRequest, settings: Config):
    try:
        return generate_improvement(request, settings)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/improvements/revisions", response_model=RevisionReview)
def revisions(request: RevisionRequest, settings: Config):
    try:
        return review_revision(request, settings)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def run_korean(
    patent_data,
    patent_name,
    oa_data,
    oa_name,
    settings,
    references=None,
    amendments=None,
    version_history=None,
):
    # Lazy import keeps the existing US execution path independent.
    from backend.jurisdictions.korean import analyze_korean

    try:
        return analyze_korean(
            patent_data,
            patent_name,
            oa_data,
            oa_name,
            settings.max_document_chars,
            references,
            amendments,
            version_history,
        )
    except DocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/health")
def health(settings: Config):
    return {"status": "ok", "provider": settings.llm_provider, "version": "0.1.0"}


def run_analysis(patent, oa, settings):
    try:
        return analyze(patent, oa, settings)
    except (DocumentError, ExtractionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/analyze/text", response_model=AnalysisResult)
def analyze_text(request: TextAnalysisRequest, settings: Config, jurisdiction: Jurisdiction = "US"):
    if jurisdiction.upper() == "KR":
        return run_korean(
            request.patent_text.encode("utf-8"),
            "patent.txt",
            request.office_action_text.encode("utf-8"),
            "office_action.xml"
            if request.office_action_text.lstrip().startswith("<")
            else "office_action.txt",
            settings,
        )
    try:
        patent = from_text(request.patent_text, "patent.txt", "patent", settings.max_document_chars)
        oa = from_text(
            request.office_action_text,
            "office_action.txt",
            "office_action",
            settings.max_document_chars,
        )
    except DocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return run_analysis(patent, oa, settings)


@app.post("/analyze/files", response_model=AnalysisResult)
async def analyze_files(
    patent: UploadFile,
    office_action: UploadFile,
    settings: Config,
    jurisdiction: Jurisdiction = "US",
    references: list[UploadFile] | None = None,
    amendments: list[UploadFile] | None = None,
    version_history: Annotated[str | None, Form(max_length=20000)] = None,
):
    adapter = LocalAdapter(settings)
    documents = []
    korean_inputs = []
    reference_inputs = []
    amendment_inputs = []
    try:
        if len(references or []) > 10:
            raise HTTPException(
                status_code=422, detail="인용발명은 최대 10개까지 입력할 수 있습니다."
            )
        for upload, kind in [(patent, "patent"), (office_action, "office_action")]:
            data = await upload.read(settings.max_upload_mb * 1024 * 1024 + 1)
            if len(data) > settings.max_upload_mb * 1024 * 1024:
                raise HTTPException(
                    status_code=413,
                    detail=f"파일 크기는 {settings.max_upload_mb} MB까지 지원합니다.",
                )
            if jurisdiction.upper() == "KR":
                korean_inputs.extend([data, upload.filename or "upload"])
            else:
                documents.append(
                    await run_in_threadpool(adapter.read, data, upload.filename or "upload", kind)
                )
        for upload in references or []:
            data = await upload.read(settings.max_upload_mb * 1024 * 1024 + 1)
            if len(data) > settings.max_upload_mb * 1024 * 1024:
                raise HTTPException(
                    status_code=413, detail="인용발명 파일 크기 한도를 초과했습니다."
                )
            reference_inputs.append((upload.filename or "reference.pdf", data))
        if len(amendments or []) > 10:
            raise HTTPException(
                status_code=422, detail="보정본은 최대 10개까지 입력할 수 있습니다."
            )
        for upload in amendments or []:
            data = await upload.read(settings.max_upload_mb * 1024 * 1024 + 1)
            if len(data) > settings.max_upload_mb * 1024 * 1024:
                raise HTTPException(status_code=413, detail="보정본 파일 크기 한도를 초과했습니다.")
            amendment_inputs.append((upload.filename or "amended.pdf", data))
    except DocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await patent.close()
        await office_action.close()
        for upload in references or []:
            await upload.close()
        for upload in amendments or []:
            await upload.close()
    if jurisdiction.upper() == "KR":
        try:
            history = json.loads(version_history) if version_history else None
            if history is not None and not isinstance(history, dict):
                raise ValueError("history must be an object")
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail="version_history는 JSON 객체여야 합니다."
            ) from exc
        return await run_in_threadpool(
            run_korean, *korean_inputs, settings, reference_inputs, amendment_inputs, history
        )
    return await run_in_threadpool(run_analysis, *documents, settings)
