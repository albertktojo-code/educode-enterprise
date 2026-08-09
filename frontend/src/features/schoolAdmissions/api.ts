import { api } from '../../lib/api'
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
}
