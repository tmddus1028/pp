/**
 * Shapes of the view models built in backend/view/ (plain dicts, so not in the OpenAPI spec).
 * The analysis contract itself comes from the generated api-types.ts.
 */
import type { components } from "./api-types";

type Schemas = components["schemas"];
export type AnalysisResult = Schemas["AnalysisResult"];
export type Rejection = Schemas["Rejection"];
export type Evidence = Schemas["Evidence"];
export type Page = Schemas["Page"];
export type GraphNode = Schemas["GraphNode"];
export type GraphEdge = Schemas["GraphEdge"];

export type CaseStatus = "open" | "in_progress" | "responded" | "closed";
export const CASE_STATUS: Record<CaseStatus, string> = {
  open: "대응 필요",
  in_progress: "검토 중",
  responded: "대응 완료",
  closed: "종결",
};

export type CaseMeta = {
  id: number;
  analysis_id: string;
  title: string;
  jurisdiction: "US" | "KR";
  status: CaseStatus;
  deadline: string | null;
  created_at: string;
};
export type CaseListItem = CaseMeta & { direct_count: number; rejection_count: number };

/** backend/view/review_model.py build_review_model() item. Fields vary by kind. */
export type ViewItem = {
  id: string;
  kind: "claim" | "rejection" | "citation" | "specification";
  title: string;
  text: string;
  evidence: Evidence;
  rejection_ids: string[];
  claim_number?: number;
  direct?: string[];
  indirect?: string[];
  objected?: string[];
  depends_on?: number[];
  children?: number[];
  status?: string;
  status_evidence?: Evidence | null;
  conditional_allowance?: boolean;
  support_ids?: string[];
  action_type?: "rejection" | "objection";
  citation_role?: string;
  figure?: string | null;
  reference?: Record<string, unknown>;
  occurrences?: { rejection_id: string | null; citation_id: string; role: string; evidence: Evidence; claim_numbers: number[] }[];
  affected_claims?: number[];
};

export type Annotation = {
  id: string;
  item_id: string;
  document_id: string;
  page: number;
  type: "direct_rejection" | "dependency" | "unaddressed" | "citation" | "specification";
  claim_number: number | null;
  statute: string | null;
  evidence_text: string;
  start: number;
  end: number;
  linked_rejection_id: string | null;
  linked_rejection_ids: string[];
  /** Normalized 0–1 page rectangles [x0, y0, x1, y1]. */
  boxes: number[][];
  bbox: number[] | null;
  match_coverage?: number;
  location_method: string;
};

export type ReviewModel = {
  analysis_id: string;
  provider: string;
  documents: { id: string; filename: string; kind: string; pages: Page[]; ocr_pages: number[] }[];
  items: ViewItem[];
  annotations: Annotation[];
  rejections: Rejection[];
  impacts: Schemas["Impact"][];
  warnings: string[];
  claim_summary: Schemas["ClaimSummary"];
};

export type RelationshipModel = {
  analysis_id: string;
  nodes: (GraphNode & { item_id: string | null })[];
  edges: Pick<GraphEdge, "source" | "target" | "relation" | "citation_role">[];
  items: ViewItem[];
  rejections: Rejection[];
  impacts: Schemas["Impact"][];
  documents: { filename: string; kind: string }[];
};

/** backend/view/models.py claim_rows() row. */
export type ClaimRow = ViewItem & {
  claim_number: number;
  role: "direct_rejection" | "dependency" | "unaddressed";
  label: string;
  statutes: string[];
  rejections: Rejection[];
};

export type CaseDetail = {
  case: CaseMeta;
  result: AnalysisResult;
  review: ReviewModel;
  relationship: RelationshipModel;
  claim_rows: ClaimRow[];
  terms: Record<string, string>;
};
