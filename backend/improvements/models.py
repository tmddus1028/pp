from typing import Literal

from pydantic import Field

from backend.schemas import AnalysisResult, Evidence, Model


class ImprovementRequest(Model):
    analysis: AnalysisResult
    claim_number: int = Field(gt=0, le=10000)
    rejection_id: str | None = None


class ReviewEvidence(Model):
    evidence_id: str
    kind: Literal[
        "claim", "parent_claim", "office_action", "status", "specification", "citation_mention"
    ]
    label: str
    evidence: Evidence
    navigation_item: str


class Grounding(Model):
    evidence_id: str
    quote: str = Field(min_length=1, max_length=4000)


class Basis(Model):
    rejection_id: str
    statute: str
    problem: str
    evidence_ids: list[str] = Field(min_length=1)


class ElementComparison(Model):
    claim_element: str
    examiner_position: str
    assessment: Literal["examiner_asserted", "not_verified"]
    evidence_ids: list[str] = Field(min_length=1)


class Strategy(Model):
    title: str
    description: str
    target_elements: list[str] = Field(min_length=1)
    action_type: Literal[
        "clarify",
        "narrow",
        "add_limitation",
        "remove_unsupported_scope",
        "dependency_rewrite",
        "argument_only",
        "other",
    ]
    evidence_ids: list[str] = Field(min_length=1)
    grounding: list[Grounding] = Field(min_length=1)
    expected_effect: str
    tradeoff: str


class Example(Model):
    available: bool
    text: str | None
    disclaimer: str
    evidence_ids: list[str]
    grounding: list[Grounding]


class ClaimImprovementSuggestion(Model):
    claim_number: int
    jurisdiction: Literal["us", "kr"]
    issue_summary: str
    rejection_basis: list[Basis]
    element_comparison: list[ElementComparison]
    strategies: list[Strategy] = Field(max_length=8)
    optional_example: Example
    missing_evidence: list[str]
    cautions: list[str]


class ImprovementResponse(Model):
    analysis_id: str
    claim_number: int
    rejection_id: str | None
    evidence_hash: str
    provider: str
    status: Literal["review", "limited", "abstained"]
    suggestion: ClaimImprovementSuggestion
    sources: list[ReviewEvidence]
    limitations: list[str]
