import { api, apiBlob } from '../../lib/api'
import type { Classroom } from '../../types/education'

export interface SchoolUnit {
  id: string
  organization_id: string
  name: string
  code: string
  address: Record<string, string>
  is_active: boolean
  created_at: string
}

export interface CapacitySnapshot {
  classroom_id: string
  classroom_name: string
  maximum_seats: number
  occupied_seats: number
  reserved_seats: number
  available_seats: number
  waitlist_size: number
  reservation_duration_minutes: number
  waitlist_enabled: boolean
}

export interface EnrollmentApplication {
  id: string
  student_profile_id: string
  student_name: string
  school_unit_id: string
  school_unit_name: string
  classroom_id: string
  classroom_name: string
  academic_year: number
  intended_grade: string
  intended_shift: string
  status: string
  submitted_at: string
}

export interface AdmissionsDashboard {
  applications: EnrollmentApplication[]
  capacities: CapacitySnapshot[]
  submitted: number
  under_review: number
  waitlisted: number
  approved: number
}

export interface EnrollmentDocumentRequirement {
  id: string
  organization_id: string
  school_unit_id?: string | null
  code: string
  name: string
  description: string
  is_required: boolean
  accepted_mime_types: string[]
  max_size_bytes: number
  retention_days: number
  is_active: boolean
  created_at: string
}

export interface EnrollmentDocumentVersion {
  id: string
  version_number: number
  original_filename: string
  content_type: string
  size_bytes: number
  checksum_sha256: string
  uploaded_by_user_id: string
  created_at: string
  download_path: string
}

export interface EnrollmentDocumentReview {
  id: string
  document_version_id: string
  decision: string
  note: string
  reviewed_by_user_id: string
  created_at: string
}

export interface EnrollmentDocument {
  id: string
  application_id: string
  requirement_id: string
  requirement_code: string
  requirement_name: string
  status: string
  current_version_number: number
  reviewed_by_user_id?: string | null
  reviewed_at?: string | null
  review_note: string
  expires_at?: string | null
  versions: EnrollmentDocumentVersion[]
  reviews: EnrollmentDocumentReview[]
  created_at: string
  updated_at: string
}

export interface EnrollmentDocumentChecklistItem {
  requirement: EnrollmentDocumentRequirement
  document?: EnrollmentDocument | null
}

export interface EnrollmentContractTemplate {
  id: string
  organization_id: string
  school_unit_id?: string | null
  code: string
  name: string
  body_template: string
  is_active: boolean
  created_at: string
}

export interface EnrollmentGuardianOption { id: string; full_name: string; email: string }

export interface EnrollmentContractVersion {
  id: string
  version_number: number
  rendered_content: string
  variables_snapshot: Record<string, string>
  content_sha256: string
  created_at: string
}

export interface EnrollmentContract {
  id: string
  application_id: string
  template_id: string
  template_name: string
  guardian_profile_id?: string | null
  guardian_name?: string | null
  status: string
  current_version_number: number
  void_reason: string
  versions: EnrollmentContractVersion[]
  acceptance?: { accepted_name: string; acceptance_hash: string; accepted_at: string } | null
  created_at: string
  updated_at: string
}

export const schoolAdmissionsApi = {
  dashboard: () => api.get<AdmissionsDashboard>('/school-admissions/dashboard'),
  units: () => api.get<SchoolUnit[]>('/school-admissions/units'),
  classrooms: () => api.get<Classroom[]>('/classrooms'),
  createUnit: (input: { name: string; code: string }) =>
    api.post<SchoolUnit>('/school-admissions/units', { ...input, address: {} }),
  placeClassroom: (classroomId: string, schoolUnitId: string, shift: string) =>
    api.patch<Classroom>(`/classrooms/${classroomId}`, {
      school_unit_id: schoolUnitId,
      shift,
    }),
  configureCapacity: (
    classroomId: string,
    input: {
      maximum_seats: number
      reservation_duration_minutes: number
      waitlist_enabled: boolean
    },
  ) => api.put<CapacitySnapshot>(`/school-admissions/classrooms/${classroomId}/capacity`, input),
  reserve: (applicationId: string) =>
    api.post(`/school-admissions/applications/${applicationId}/reserve`),
  approve: (applicationId: string) =>
    api.post(`/school-admissions/applications/${applicationId}/approve`),
  documentRequirements: (schoolUnitId?: string) =>
    api.get<EnrollmentDocumentRequirement[]>(
      `/school-admissions/document-requirements${schoolUnitId ? `?school_unit_id=${schoolUnitId}` : ''}`,
    ),
  createDocumentRequirement: (input: {
    school_unit_id?: string | null
    code: string
    name: string
    description: string
    is_required: boolean
    accepted_mime_types: string[]
    max_size_bytes: number
    retention_days: number
  }) => api.post<EnrollmentDocumentRequirement>('/school-admissions/document-requirements', input),
  documentChecklist: (applicationId: string) =>
    api.get<EnrollmentDocumentChecklistItem[]>(
      `/school-admissions/applications/${applicationId}/documents`,
    ),
  uploadDocument: (applicationId: string, requirementId: string, file: File) => {
    const body = new FormData()
    body.append('requirement_id', requirementId)
    body.append('file', file)
    return api<EnrollmentDocument>(`/school-admissions/applications/${applicationId}/documents`, {
      method: 'POST',
      body,
    })
  },
  reviewDocument: (
    documentId: string,
    input: { decision: string; note: string; expires_at?: string | null },
  ) => api.post<EnrollmentDocument>(`/school-admissions/documents/${documentId}/review`, input),
  downloadDocument: (downloadPath: string) => apiBlob(downloadPath),
  contractTemplates: () =>
    api.get<EnrollmentContractTemplate[]>('/school-admissions/contract-templates'),
  createContractTemplate: (input: {
    school_unit_id?: string | null
    code: string
    name: string
    body_template: string
  }) => api.post<EnrollmentContractTemplate>('/school-admissions/contract-templates', input),
  contracts: () => api.get<EnrollmentContract[]>('/school-admissions/contracts'),
  applicationGuardians: (applicationId: string) =>
    api.get<EnrollmentGuardianOption[]>(`/school-admissions/applications/${applicationId}/guardians`),
  generateContract: (applicationId: string, input: { template_id: string; guardian_profile_id: string }) =>
    api.post<EnrollmentContract>(`/school-admissions/applications/${applicationId}/contract`, input),
  voidContract: (contractId: string, reason: string) =>
    api.post<EnrollmentContract>(`/school-admissions/contracts/${contractId}/void`, { reason }),
}
