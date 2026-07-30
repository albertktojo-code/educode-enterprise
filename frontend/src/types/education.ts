export type ProjectStatus = 'draft' | 'active' | 'archived'
export type ContentType =
  | 'lesson'
  | 'comic'
  | 'quiz'
  | 'activity'
  | 'reference'
export type EnrollmentRole = 'student' | 'teacher' | 'assistant'

export interface Subject {
  id: string
  organization_id: string
  name: string
  code: string
  description?: string | null
  is_active: boolean
  created_at: string
}

export interface Classroom {
  id: string
  organization_id: string
  name: string
  subject_id?: string | null
  school_year?: number | null
  grade?: string | null
  description?: string | null
  is_active: boolean
  created_at: string
}

export interface DirectoryUser {
  id: string
  full_name: string
  email: string
  organization_role: string
}

export interface Enrollment {
  id: string
  classroom_id: string
  user_id: string
  full_name: string
  email: string
  role: EnrollmentRole
  created_at: string
}

export interface Project {
  id: string
  organization_id: string
  owner_id: string
  title: string
  description?: string | null
  status: ProjectStatus
  classroom_id?: string | null
  subject_id?: string | null
  created_at: string
  updated_at: string
}

export interface ContentItem {
  id: string
  project_id: string
  title: string
  content_type: ContentType
  body?: string | null
  position: number
  is_published: boolean
  created_at: string
}

export interface DashboardSummary {
  subjects: number
  classrooms: number
  active_classrooms: number
  users: number
  projects: number
  draft_projects: number
  active_projects: number
  archived_projects: number
  contents: number
  published_contents: number
  documents: number
  ready_documents: number
}
