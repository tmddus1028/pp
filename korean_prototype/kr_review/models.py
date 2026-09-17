from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Evidence(Model):
    document_id: str
    text: str
    start: int
    end: int
    page_numbers: list[int] = Field(default_factory=list)
    xml_path: str | None = None


class Page(Model):
    number: int
    text: str
    start: int
    end: int


class Document(Model):
    document_id: str
    filename: str
    kind: Literal["patent", "office_action", "reference"]
    text: str
    pages: list[Page] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class Claim(Model):
    number: int
    text: str
    depends_on: list[int] = Field(default_factory=list)
    status: Literal["active", "canceled"] = "active"
    evidence: Evidence


class Citation(Model):
    citation_id: str
    publication_number: str
    title: str = ""
    role: Literal["relied_upon"] = "relied_upon"
    evidence: Evidence
    document_id: str | None = None


class Rejection(Model):
    rejection_id: str
    claims: list[int]
    statute: str
    explanation: str
    evidence: Evidence
    citation_ids: list[str] = Field(default_factory=list)


class AnalysisResult(Model):
    jurisdiction: Literal["KR"] = "KR"
    application_number: str = ""
    title: str = ""
    office_action_date: str = ""
    documents: list[Document]
    claims: list[Claim]
    rejections: list[Rejection]
    citations: list[Citation]
    direct_claims: list[int]
    dependency_claims: list[int]
    warnings: list[str] = Field(default_factory=list)


class ReviewError(ValueError):
    """A user-readable prototype input or provider error."""
