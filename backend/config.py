from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: Literal["local", "openai", "azure"] = "local"
    improvement_provider: Literal["inherit", "local", "local_ollama", "openai", "azure", "qwen"] = (
        "inherit"
    )
    qwen_api_key: str = Field(default="", repr=False)
    qwen_base_url: str = ""
    qwen_model: str = ""
    qwen_response_format: Literal["json_object", "json_schema"] = "json_object"
    local_llm_base_url: str = "http://127.0.0.1:11434"
    local_llm_model: str = ""
    local_embedding_model: str = ""
    local_llm_timeout_seconds: float = Field(default=180, gt=0, le=600)
    local_llm_context_tokens: int = Field(default=32768, ge=8192, le=131072)
    openai_api_key: str = Field(default="", repr=False)
    openai_model: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = Field(default="", repr=False)
    azure_openai_deployment: str = ""
    llm_timeout_seconds: float = Field(default=60, gt=0, le=300)
    max_upload_mb: int = Field(default=20, ge=1, le=100)
    max_pdf_pages: int = Field(default=150, ge=1, le=1000)
    max_document_chars: int = Field(default=500_000, ge=1000, le=2_000_000)
    oa_chunk_chars: int = Field(default=14_000, ge=1000, le=30_000)
    tesseract_cmd: str = ""
    ocr_dpi: int = Field(default=300, ge=150, le=600)
    ocr_min_text_chars: int = Field(default=20, ge=1, le=1000)
    ocr_timeout_seconds: float = Field(default=60, gt=0, le=300)
    ocr_max_pixels: int = Field(default=40_000_000, ge=1_000_000, le=100_000_000)
    ocr_renderer: Literal["auto", "pymupdf", "pdfium"] = "auto"
