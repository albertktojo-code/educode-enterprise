export type HealthResponse = {
  status: 'healthy'
  service: string
  environment: string
  database: 'connected'
  ai_provider: string
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${API_URL}/health`, { signal })
  if (!response.ok) {
    throw new Error(`Falha na API: HTTP ${response.status}`)
  }
  return response.json() as Promise<HealthResponse>
}
