import { API_URL, api } from '../../lib/api'
import type {
  CertificateIssueInput,
  CertificateStudent,
  PortfolioCertificate,
  PortfolioEvidence,
  PublicCertificate,
} from './types'

const ROOT = '/student/portfolio'

export const credentialsApi = {
  students: () => api.get<CertificateStudent[]>(`${ROOT}/educator/students`),
  evidence: (studentId: string) =>
    api.get<PortfolioEvidence[]>(`${ROOT}/educator/students/${studentId}/entries`),
  certificates: (studentId: string) =>
    api.get<PortfolioCertificate[]>(`${ROOT}/educator/students/${studentId}/certificates`),
  ownCertificates: () => api.get<PortfolioCertificate[]>(`${ROOT}/certificates`),
  issue: (input: CertificateIssueInput) =>
    api.post<PortfolioCertificate>(`${ROOT}/certificates`, input),
  revoke: (certificateId: string, reason: string) =>
    api.post<PortfolioCertificate>(`${ROOT}/certificates/${certificateId}/revoke`, { reason }),
  verify: (code: string) =>
    api.get<PublicCertificate>(`${ROOT}/certificates/verify/${encodeURIComponent(code)}`, { auth: false }),
  qrUrl: (code: string, origin: string) =>
    `${API_URL}${ROOT}/certificates/verify/${encodeURIComponent(code)}/qr?origin=${encodeURIComponent(origin)}`,
}
