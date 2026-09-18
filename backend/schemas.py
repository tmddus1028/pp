from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Page(Model):
    number: int = Field(ge=1)
    text: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class RemovedMargin(Model):
    page_number: int
    text: str
    position: Literal["header", "footer"]
    reason: str


class OCRWord(Model):
    text: str
    # Normalized image coordinates, origin top-left; source PDF is never annotated.
    bbox: tuple[float, float, float, float]
    block: int
    line: int
    confidence: float

    @model_validator(mode="after")
    def valid_bbox(self):
        x1, y1, x2, y2 = self.bbox
        if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
            raise ValueError("OCR bbox must be a nonempty normalized rectangle")
        return self


class OCRMetadata(Model):
    pdf_parser: Literal["pymupdf", "pdfium", "pypdf"] | None = None
    pdf_text_extractors: dict[int, str] = Field(default_factory=dict)
    pdf_layout_pages: list[int] = Field(default_factory=list)
    ocr_used: bool = False
    ocr_pages: list[int] = Field(default_factory=list)
    ocr_engine: Literal["tesseract"] | None = None
    ocr_renderer: Literal["pymupdf", "pdfium"] | None = None
    ocr_dpi: int | None = None
    ocr_language: str | None = None
    # Unmodified Tesseract output, before the existing whitespace/NFKC normalizer.
    ocr_raw_text: dict[int, str] = Field(default_factory=dict)
    removed_margins: list[RemovedMargin] = Field(default_factory=list)
    ocr_words: dict[int, list[OCRWord]] = Field(default_factory=dict)


class Document(Model):
    document_id: str
    filename: str
    kind: Literal["patent", "office_action", "reference"]
    text: str
    pages: list[Page]
    warnings: list[str] = Field(default_factory=list)
    metadata: OCRMetadata = Field(default_factory=OCRMetadata)
    source_metadata: dict = Field(default_factory=dict)


class Evidence(Model):
    document_id: str
    text: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    page_numbers: list[int]
    xml_path: str | None = None


class Claim(Model):
    claim_number: int = Field(gt=0, le=10000)
    text: str
    independent: bool
    depends_on: list[int]
    status: Literal["active", "canceled"] = "active"
    evidence: Evidence

    @model_validator(mode="after")
    def consistent_dependency(self):
        if self.independent != (not self.depends_on):
            raise ValueError("independent must agree with depends_on")
        return self


class Patent(Model):
    document_id: str
    claims: list[Claim]
    warnings: list[str] = Field(default_factory=list)


class CitedReference(Model):
    citation_id: str
    name: str | None
    publication_number: str | None
    evidence: Evidence
    definition_evidence: Evidence | None = None
    type: Literal["patent", "npl", "unknown"] = "unknown"
    raw_text: str = ""
    publication: str | None = None
    year: int | None = None
    title: str | None = None
    doi: str | None = None
    bibliographic_locator: str | None = None
    canonical_key: str = ""
    citation_role: Literal["relied_upon", "supporting_evidence", "not_relied_upon"] = "relied_upon"
    explicit_alias: bool = False
    source_document_id: str | None = None


class CitationDocument(Model):
    citation_id: str
    canonical_key: str
    display_name: str
    authors: list[str]
    title: str | None = None
    publication_number: str | None = None
    doi: str | None = None
    journal: str | None = None
    year: int | None = None
    type: Literal["patent", "npl", "unknown"]
    citation_role: Literal["relied_upon", "supporting_evidence", "not_relied_upon"]
    citation_roles: list[str]
    evidence: Evidence
    source_document_id: str | None = None


class RejectionCitation(Model):
    rejection_id: str | None
    citation_id: str
    role: Literal["relied_upon", "supporting_evidence", "not_relied_upon"]
    evidence: Evidence
    claim_numbers: list[int] = Field(default_factory=list)


class Rejection(Model):
    rejection_id: str
    action_type: Literal["rejection", "objection"]
    statute: str
    claims: list[int]
    primary_claims: list[int] = Field(default_factory=list)
    reason_summary: str
    examiner_explanation: str
    cited_references: list[CitedReference]
    evidence: Evidence
    extraction_method: Literal["local", "openai", "azure"]
    statute_code: str = ""
    raw_statute_text: str = ""
    subject: str = "claims"


class ReviewItem(Model):
    item_id: str
    rejection_id: str
    claim_numbers: list[int]
    text: str
    evidence: Evidence


class ClaimDisposition(Model):
    claim_number: int
    status: Literal[
        "rejected", "objected", "allowed", "withdrawn", "canceled", "pending", "unknown"
    ]
    evidence: Evidence | None = None
    conditional_allowance: bool = False
    raw_status: str = ""
    source_status: str = ""


class ClaimSummary(Model):
    direct_rejected_claims: list[int] = Field(default_factory=list)
    objected_claims: list[int] = Field(default_factory=list)
    allowed_claims: list[int] = Field(default_factory=list)
    withdrawn_claims: list[int] = Field(default_factory=list)
    canceled_claims: list[int] = Field(default_factory=list)
    pending_claims: list[int] = Field(default_factory=list)
    unknown_claims: list[int] = Field(default_factory=list)
    dependency_impacted_claims: list[int] = Field(default_factory=list)


class Impact(Model):
    rejection_id: str
    direct_claims: list[int]
    objected_claims: list[int] = Field(default_factory=list)
    dependency_impacted_claims: list[int]
    missing_claims: list[int]
    citations: list[str]
    review_items: list[ReviewItem] = Field(default_factory=list)


class GraphNode(Model):
    id: str
    label: str
    kind: Literal["office_action", "rejection", "claim", "citation"]
    status: str = ""
    claim_number: int | None = None


class GraphEdge(Model):
    source: str
    target: str
    relation: Literal["contains", "directly_addresses", "depends_on", "cites"]
    evidence: Evidence | None = None
    citation_role: str | None = None


class Graph(Model):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class AnalysisResult(Model):
    schema_version: str = "1.0"
    analysis_id: str
    provider: str
    documents: list[Document]
    patent: Patent
    rejections: list[Rejection]
    impacts: list[Impact]
    graph: Graph
    warnings: list[str]
    claim_statuses: list[ClaimDisposition] = Field(default_factory=list)
    claim_summary: ClaimSummary = Field(default_factory=ClaimSummary)
    citations: list[CitationDocument] = Field(default_factory=list)
    rejection_citations: list[RejectionCitation] = Field(default_factory=list)
    evidence_links: list[dict] = Field(default_factory=list)
    claim_version: dict = Field(default_factory=dict)


class TextAnalysisRequest(Model):
    patent_text: str = Field(min_length=1, max_length=500000)
    office_action_text: str = Field(min_length=1, max_length=500000)
