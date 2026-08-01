export type Role = 'owner' | 'admin' | 'teacher' | 'member'

export interface Organization {
  id: string
  name: string
  slug: string
}

export interface OrganizationDetails extends Organization {
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Membership {
  id: string
  role: Role
  organization: Organization
}

export interface User {
  id: string
  email: string
  full_name: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
  memberships: Membership[]
}

export interface TokenPair {
  access_token: string
  refresh_token?: string | null
  token_type: string
  expires_in: number
  session_id?: string | null
  remember_me: boolean
}

export interface AuthSession {
  id: string
  device_name: string
  last_ip_masked: string
  remember_me: boolean
  created_at: string
  last_used_at: string
  expires_at: string
  idle_expires_at: string
  current: boolean
}

export interface UserListItem {
  id: string
  email: string
  full_name: string
  is_active: boolean
  role: Role
  created_at: string
}
