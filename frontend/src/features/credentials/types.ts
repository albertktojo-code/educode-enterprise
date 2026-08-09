export type CertificateStatus = 'active' | 'revoked'

export interface CertificateStudent {
  id: string
  full_name: string
  email: string
}

export interface PortfolioEvidence {
  id: string
  assignment_id: string
  attempt_id: string
  title_snapshot: string
  assignment_type_snapshot: string
  percentage_snapshot: number
  reflection: string
  revision: number
  completed_at_snapshot: string | null
}

export interface PortfolioCertificate {
  id: string
  title: string
  description: string
  verification_code: string
  evidence_entry_ids: string[]
  status: CertificateStatus
  issued_at: string
  revoked_at: string | null
  revocation_reason: string
}

export interface PublicCertificateEvidence {
  title: string
  assignment_type: string
  percentage: number
}

export interface PublicCertificate {
  title: string
  description: string
  verification_code: string
  status: CertificateStatus
  issued_at: string
  revoked_at: string | null
  revocation_reason: string
  student_name: string
  issuer_name: string
  organization_name: string
  evidence: PublicCertificateEvidence[]
}

export interface CertificateIssueInput {
  student_user_id: string
  title: string
  description: string
  evidence_entry_ids: string[]
}
