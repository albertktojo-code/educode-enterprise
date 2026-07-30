export type RetrievalSourceKind = 'learning_unit' | 'generation_source'
export type RetrievalIndexStatus =
  | 'not_indexed'
  | 'processing'
  | 'indexed'
  | 'stale'
  | 'failed'
export type SearchMode = 'semantic' | 'text' | 'hybrid'
export type FeedbackRating = 'relevant' | 'partial' | 'irrelevant'

export interface RetrievalIndexJob {
  id: string
  organization_id: string
  created_by_user_id: string
  source_kind: RetrievalSourceKind
  document_id?: string | null
  chapter_id?: string | null
  learning_unit_id?: string | null
  generation_source_id?: string | null
  source_title: string
  status: RetrievalIndexStatus
  progress: number
  current_step?: string | null
  error_message?: string | null
  chunk_target_chars: number
  chunk_overlap_chars: number
  chunk_min_chars: number
  chunking_version: string
  embedding_provider: string
  embedding_model: string
  embedding_dimension: number
  source_checksum?: string | null
  indexing_revision: number
  active_chunk_count: number
  security_flag_count: number
  created_at: string
  updated_at: string
  indexed_at?: string | null
}

export interface RetrievalStats {
  total_jobs: number
  indexed_jobs: number
  processing_jobs: number
  stale_jobs: number
  failed_jobs: number
  active_chunks: number
  flagged_chunks: number
  feedback_total: number
  relevant_feedback: number
  partial_feedback: number
  irrelevant_feedback: number
}

export interface RetrievalChunk {
  id: string
  index_job_id: string
  source_kind: RetrievalSourceKind
  document_id?: string | null
  chapter_id?: string | null
  learning_unit_id?: string | null
  generation_source_id?: string | null
  heading?: string | null
  page_start?: number | null
  page_end?: number | null
  source_order: number
  chunk_index: number
  content: string
  character_count: number
  token_estimate: number
  security_flag: boolean
  security_notes?: string | null
  indexing_revision: number
  metadata_json: Record<string, unknown>
}

export interface SearchResult {
  chunk_id: string
  index_job_id: string
  source_kind: RetrievalSourceKind
  heading?: string | null
  document_id?: string | null
  chapter_id?: string | null
  learning_unit_id?: string | null
  generation_source_id?: string | null
  page_start?: number | null
  page_end?: number | null
  source_order: number
  chunk_index: number
  content: string
  vector_score?: number | null
  text_score?: number | null
  hybrid_score?: number | null
  matched_terms: string[]
  security_flag: boolean
  explanation: string
}

export interface OrderedContextItem {
  chunk_id: string
  citation_label: string
  source_order: number
  content: string
}

export interface SearchResponse {
  query: string
  mode: SearchMode
  total_candidates: number
  results: SearchResult[]
  ordered_context: OrderedContextItem[]
}
