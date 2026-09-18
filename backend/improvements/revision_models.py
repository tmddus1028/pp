"""Separate revision objects; the original AnalysisResult is never updated."""

from typing import Literal

from pydantic import ConfigDict, Field

from backend.improvements.models import Grounding, ImprovementRequest, ReviewEvidence
from backend.schemas import Model

ChangeType = Literal["added", "removed", "changed", "unchanged"]


class RevisionRequest(ImprovementRequest):
    revised_text: str = Field(min_length=1, max_length=12000)
    parent_revision_id: str | None = Field(default=None, max_length=80)


class ClaimRevision(Model):
    model_config = ConfigDict(extra="forbid", frozen=True)
    original_claim_number: int
    revision_id: str
    text: str
    text_hash: str
    parent_revision_id: str | None
    created_at: str


class TextChange(Model):
    change_type: ChangeType
    original: str
    revised: str
    original_start: int
    original_end: int
    revised_start: int
    revised_end: int


class RevisionElement(Model):
    element_id: str
    element: str
    change_type: Literal["added", "changed", "unchanged"]
    start: int
    end: int
    candidate_evidence_ids: list[str]


class ElementSupport(Model):
    element_id: str
    status: Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "NOT_FOUND", "UNCERTAIN"]
    evidence_ids: list[str]
    grounding: list[Grounding]
    reason: str


class RejectionResponse(Model):
    rejection_id: str
    status: Literal[
        "POTENTIALLY_ADDRESSES", "PARTIALLY_ADDRESSES", "DOES_NOT_ADDRESS", "INSUFFICIENT_EVIDENCE"
    ]
    reason: str
    evidence_ids: list[str]
    grounding: list[Grounding]
    prior_art_assessment: Literal["OA_ONLY", "INSUFFICIENT_EVIDENCE", "PROVIDED_EXCERPTS"]


class RevisionAssessment(Model):
    revision_summary: str
    specification_support: list[ElementSupport]
    rejection_response: list[RejectionResponse]
    remaining_issues: list[str]
    cautions: list[str]


class Similarity(Model):
    method: str
    original_claim: float | None
    specification: dict[str, float | None]
    note: str


class RevisionReview(Model):
    analysis_id: str
    rejection_id: str | None
    evidence_hash: str
    cache_key: str
    provider: str
    revision: ClaimRevision
    claim_changes: list[TextChange]
    elements: list[RevisionElement]
    assessment: RevisionAssessment
    new_matter_risks: list[str]
    similarity: Similarity
    sources: list[ReviewEvidence]
    limitations: list[str]
