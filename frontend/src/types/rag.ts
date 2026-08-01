export type RagContextStatus =
  | 'draft'
  | 'in_review'
  | 'ready_with_warnings'
  | 'insufficient'
  | 'conflicted'
  | 'approved'
  | 'archived'
export type RagReviewStatus = 'pending' | 'approved' | 'rejected'
export type RagSourceSafety = 'safe' | 'suspicious' | 'blocked' | 'manually_approved'

export interface RagContextSummary {
  id: string
  generation_project_id: string
  title: string
  query: string
  search_mode: string
  status: RagContextStatus
  context_version: number
  quality_score: number
  source_count: number
  fact_count: number
  open_conflict_count: number
  updated_at: string
}

export interface RagSource {
  id: string
  chunk_id: string
  citation_code: string
  citation_label: string
  ranking_position: number
  source_order: number
  inclusion_reason: string
  is_mandatory: boolean
  is_included: boolean
  safety_status: RagSourceSafety
  content_snapshot: string
  page_start?: number | null
  page_end?: number | null
  created_at: string
}

export interface RagFact {
  id: string
  statement: string
  fact_type: string
  confidence: number
  citation_codes: string[]
  review_status: RagReviewStatus
  is_mandatory: boolean
  order_index: number
  created_at: string
}

export interface RagRule {
  id: string
  category: string
  rule_text: string
  priority: string
  order_index: number
}

export interface RagConflict {
  id: string
  statement_a: string
  statement_b: string
  citation_codes_a: string[]
  citation_codes_b: string[]
  description: string
  status: string
  resolution_notes?: string | null
}

export interface RagEvaluation {
  id: string
  relevance_score: number
  coverage_score: number
  diversity_score: number
  traceability_score: number
  consistency_score: number
  safety_score: number
  overall_score: number
  details: Record<string, unknown>
  created_at: string
}

export interface RagContext {
  id: string
  organization_id: string
  generation_project_id: string
  created_by_user_id: string
  approved_by_user_id?: string | null
  title: string
  query: string
  search_mode: string
  status: RagContextStatus
  context_version: number
  retrieval_configuration: Record<string, unknown>
  structured_context: Record<string, unknown>
  assembled_context_text: string
  quality_score: number
  token_estimate: number
  readiness_reason?: string | null
  notes?: string | null
  created_at: string
  updated_at: string
  approved_at?: string | null
  sources: RagSource[]
  facts: RagFact[]
  rules: RagRule[]
  conflicts: RagConflict[]
  evaluations: RagEvaluation[]
}
