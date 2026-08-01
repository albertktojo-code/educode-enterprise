export type DocumentStatus =
  | 'uploaded'
  | 'processing'
  | 'ready'
  | 'failed'

export type DocumentPageKind = 'textual' | 'scanned' | 'mixed' | 'empty'
export type TextExtractionMethod = 'native' | 'ocr' | 'none'
export type OcrStatus = 'not_required' | 'required' | 'completed' | 'failed'
export type ChapterDetectionMethod =
  | 'pdf_toc'
  | 'automatic_heading'
  | 'manual'

export interface DocumentItem {
  id: string
  organization_id: string
  uploaded_by_id: string
  project_id?: string | null
  original_filename: string
  mime_type: string
  size_bytes: number
  checksum_sha256: string
  status: DocumentStatus
  page_count?: number | null
  created_at: string
  updated_at: string
  processed_at?: string | null
}

export interface DocumentDetail extends DocumentItem {
  extracted_text?: string | null
  extraction_error?: string | null
}

export interface DocumentPageItem {
  id: string
  document_id: string
  page_number: number
  character_count: number
  image_count: number
  page_kind: DocumentPageKind
  extraction_method: TextExtractionMethod
  ocr_status: OcrStatus
  text_preview: string
}

export interface DocumentPageDetail {
  id: string
  document_id: string
  page_number: number
  text: string
  character_count: number
  image_count: number
  page_kind: DocumentPageKind
  extraction_method: TextExtractionMethod
  ocr_status: OcrStatus
  created_at: string
  updated_at: string
}

export interface DocumentChapter {
  id: string
  document_id: string
  title: string
  chapter_number?: number | null
  start_page: number
  end_page: number
  summary?: string | null
  detection_method: ChapterDetectionMethod
  confidence: number
  is_confirmed: boolean
  position: number
  created_at: string
  updated_at: string
}

export interface ChapterTextPreview {
  chapter: DocumentChapter
  text: string
  character_count: number
  source_pages: number[]
}

export interface DocumentStructureSummary {
  document_id: string
  page_count: number
  extracted_pages: number
  textual_pages: number
  mixed_pages: number
  scanned_pages: number
  empty_pages: number
  ocr_required_pages: number
  chapter_count: number
  confirmed_chapters: number
}
