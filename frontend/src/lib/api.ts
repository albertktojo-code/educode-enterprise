import type { TokenPair } from '../types/auth'

const API_URL =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

const ACCESS_TOKEN_KEY = 'educode_access_token'
const LEGACY_REFRESH_TOKEN_KEY = 'educode_refresh_token'
const PERSISTENCE_KEY = 'educode_remember_me'

type ApiOptions = RequestInit & {
  auth?: boolean
  retry?: boolean
}

let refreshPromise: Promise<boolean> | null = null

function getAccessToken(): string | null {
  return (
    sessionStorage.getItem(ACCESS_TOKEN_KEY) ??
    localStorage.getItem(ACCESS_TOKEN_KEY)
  )
}

function rememberPreference(): boolean {
  return localStorage.getItem(PERSISTENCE_KEY) === 'true'
}

function storeAccessToken(token: string, rememberMe: boolean): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  if (rememberMe) {
    localStorage.setItem(ACCESS_TOKEN_KEY, token)
    localStorage.setItem(PERSISTENCE_KEY, 'true')
  } else {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, token)
    localStorage.removeItem(PERSISTENCE_KEY)
  }
}

function clearTokens(dispatch = true): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(LEGACY_REFRESH_TOKEN_KEY)
  localStorage.removeItem(PERSISTENCE_KEY)
  if (dispatch) window.dispatchEvent(new Event('educode:logout'))
}

export async function refreshAccessToken(): Promise<boolean> {
  if (!refreshPromise) {
    const legacyRefresh = localStorage.getItem(LEGACY_REFRESH_TOKEN_KEY)
    refreshPromise = fetch(`${API_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        refresh_token: legacyRefresh || null,
      }),
    })
      .then(async (response) => {
        if (!response.ok) return false
        const tokens = (await response.json()) as TokenPair
        storeAccessToken(
          tokens.access_token,
          tokens.remember_me || rememberPreference(),
        )
        localStorage.removeItem(LEGACY_REFRESH_TOKEN_KEY)
        return true
      })
      .catch(() => false)
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

async function readError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as {
      detail?: string | Array<{ msg?: string }>
      error?: { message?: string }
    }
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.detail)) {
      return data.detail.map((item) => item.msg ?? 'Campo inválido').join('; ')
    }
    if (data.error?.message) return data.error.message
  } catch {
    // Response without a JSON error body.
  }
  return `Não foi possível concluir a operação (HTTP ${response.status}).`
}

async function apiRequest<T>(
  path: string,
  options: ApiOptions = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  if (options.auth !== false) {
    const token = getAccessToken()
    if (token) headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: options.credentials ?? 'include',
    headers,
  })

  if (
    response.status === 401 &&
    options.auth !== false &&
    options.retry !== false
  ) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      return apiRequest<T>(path, { ...options, retry: false })
    }
    clearTokens()
  }

  if (!response.ok) {
    throw new Error(await readError(response))
  }

  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = Object.assign(apiRequest, {
  get: <T>(path: string, options: ApiOptions = {}) =>
    apiRequest<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options: ApiOptions = {}) =>
    apiRequest<T>(path, {
      ...options,
      method: 'POST',
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  put: <T>(path: string, body?: unknown, options: ApiOptions = {}) =>
    apiRequest<T>(path, {
      ...options,
      method: 'PUT',
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  patch: <T>(path: string, body?: unknown, options: ApiOptions = {}) =>
    apiRequest<T>(path, {
      ...options,
      method: 'PATCH',
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  delete: <T>(path: string, options: ApiOptions = {}) =>
    apiRequest<T>(path, { ...options, method: 'DELETE' }),
})

export function saveTokens(tokens: TokenPair, rememberMe: boolean): void {
  storeAccessToken(tokens.access_token, rememberMe)
  localStorage.removeItem(LEGACY_REFRESH_TOKEN_KEY)
}

export function removeTokens(): void {
  clearTokens(false)
}

export function hasAccessToken(): boolean {
  return Boolean(getAccessToken())
}

export async function apiBlob(
  path: string,
  options: ApiOptions = {},
): Promise<Blob> {
  const headers = new Headers(options.headers)
  const token = getAccessToken()
  if (options.auth !== false && token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: options.credentials ?? 'include',
    headers,
  })

  if (
    response.status === 401 &&
    options.auth !== false &&
    options.retry !== false
  ) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      return apiBlob(path, { ...options, retry: false })
    }
    clearTokens()
  }

  if (!response.ok) {
    throw new Error(await readError(response))
  }

  return response.blob()
}
