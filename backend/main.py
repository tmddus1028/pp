from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, UploadFile
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
def analyze_text(request: TextAnalysisRequest, settings: Config):
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
async def analyze_files(patent: UploadFile, office_action: UploadFile, settings: Config):
    adapter = LocalAdapter(settings)
    documents = []
    try:
        for upload, kind in [(patent, "patent"), (office_action, "office_action")]:
            data = await upload.read(settings.max_upload_mb * 1024 * 1024 + 1)
            if len(data) > settings.max_upload_mb * 1024 * 1024:
                raise HTTPException(
                    status_code=413,
                    detail=f"파일 크기는 {settings.max_upload_mb} MB까지 지원합니다.",
                )
            documents.append(
                await run_in_threadpool(adapter.read, data, upload.filename or "upload", kind)
            )
    except DocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await patent.close()
        await office_action.close()
    return await run_in_threadpool(run_analysis, *documents, settings)
