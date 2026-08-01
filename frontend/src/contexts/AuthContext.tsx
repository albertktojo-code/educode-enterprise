/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import {
  api,
  hasAccessToken,
  refreshAccessToken,
  removeTokens,
  saveTokens,
} from '../lib/api'
import type { TokenPair, User } from '../types/auth'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login(email: string, password: string, rememberMe: boolean): Promise<void>
  logout(): Promise<void>
  refreshUser(): Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const logout = useCallback(async () => {
    try {
      await api<void>('/auth/logout', {
        method: 'POST',
        auth: false,
      })
    } catch {
      // Local logout must succeed even if the server is unavailable.
    } finally {
      removeTokens()
      setUser(null)
    }
  }, [])

  const refreshUser = useCallback(async () => {
    const currentUser = await api<User>('/auth/me')
    setUser(currentUser)
  }, [])

  const login = useCallback(
    async (email: string, password: string, rememberMe: boolean) => {
      const tokens = await api<TokenPair>('/auth/login', {
        method: 'POST',
        auth: false,
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          password,
          remember_me: rememberMe,
        }),
      })
      saveTokens(tokens, rememberMe)
      await refreshUser()
    },
    [refreshUser],
  )

  useEffect(() => {
    const handleForcedLogout = () => setUser(null)
    window.addEventListener('educode:logout', handleForcedLogout)
    return () => window.removeEventListener('educode:logout', handleForcedLogout)
  }, [])

  useEffect(() => {
    async function restore(): Promise<void> {
      try {
        if (!hasAccessToken()) {
          const restored = await refreshAccessToken()
          if (!restored) return
        }
        await refreshUser()
      } catch {
        removeTokens()
        setUser(null)
      } finally {
        setLoading(false)
      }
    }
    void restore()
  }, [refreshUser])

  const value = useMemo(
    () => ({ user, loading, login, logout, refreshUser }),
    [user, loading, login, logout, refreshUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth deve estar dentro de AuthProvider')
  }
  return context
}
