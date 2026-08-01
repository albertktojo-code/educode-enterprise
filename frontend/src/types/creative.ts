export type CreativeItemKind = 'character' | 'scene' | 'style'
export type CreativeVisibility = 'private' | 'team' | 'organization'
export type CreativeStatus = 'draft' | 'active' | 'archived'
export type SequenceStatus = 'draft' | 'in_review' | 'approved' | 'archived'

export interface CreativeAsset {
  id: string
  creative_item_id: string
  file_name: string
  mime_type: string
  size_bytes: number
  checksum_sha256: string
  asset_role: string
  pdf_page_number?: number | null
  is_primary: boolean
  created_at: string
}

export interface CreativeVersion {
  id: string
  creative_item_id: string
  version_number: number
  profile_snapshot: Record<string, unknown>
  change_description?: string | null
  created_by_user_id: string
  created_at: string
}

export interface CreativeItem {
  id: string
  organization_id: string
  created_by_user_id: string
  created_by_name_snapshot: string
  kind: CreativeItemKind
  name: string
  description?: string | null
  canonical_prompt?: string | null
  negative_prompt?: string | null
  profile_data: Record<string, unknown>
  visibility: CreativeVisibility
  status: CreativeStatus
  rights_confirmed: boolean
  original_author?: string | null
  license_notes?: string | null
  assets: CreativeAsset[]
  versions: CreativeVersion[]
  created_at: string
  updated_at: string
}

export interface CreativeCatalog {
  kinds: string[]
  character_asset_roles: string[]
  scene_asset_roles: string[]
  style_asset_roles: string[]
  cognitive_levels: string[]
  evaluation_roles: string[]
}

export interface CreativeProjectLink {
  id: string
  creative_item_id: string
  creative_version_id?: string | null
  narrative_role?: string | null
  position: number
  is_primary: boolean
  name: string
  kind: CreativeItemKind
}

export interface CreativeBible {
  id: string
  generation_project_id: string
  title: string
  age_group?: string | null
  visual_language?: string | null
  narrative_tone?: string | null
  pedagogical_tone?: string | null
  color_palette: string[]
  mandatory_rules: string[]
  prohibited_elements: string[]
  institution_identity: Record<string, unknown>
  notes?: string | null
  updated_by_user_id: string
  created_at: string
  updated_at: string
}

export interface TeachingSequenceItem {
  id?: string
  sequence_id?: string
  position: number
  title: string
  material_type: string
  learning_objective?: string | null
  pillar_codes: string[]
  duration_minutes?: number | null
  evaluation_role: string
  notes?: string | null
}

export interface TeachingSequence {
  id: string
  organization_id: string
  generation_project_id?: string | null
  title: string
  description?: string | null
  status: SequenceStatus
  created_by_user_id: string
  created_by_name_snapshot: string
  items: TeachingSequenceItem[]
  created_at: string
  updated_at: string
}
