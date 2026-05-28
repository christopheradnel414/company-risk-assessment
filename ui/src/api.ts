import type { AssessmentRequest, JobResponse, JobSummary } from './types'

const BASE = '/api/v1'

export class AuthError extends Error {
  constructor() { super('Invalid or missing API key'); this.name = 'AuthError' }
}

let _apiKey: string = localStorage.getItem('apiKey') ?? ''

export function getApiKey(): string { return _apiKey }

export function setApiKey(key: string): void {
  _apiKey = key
  if (key) localStorage.setItem('apiKey', key)
  else localStorage.removeItem('apiKey')
}

function authHeaders(): Record<string, string> {
  return _apiKey ? { 'X-API-Key': _apiKey } : {}
}

function checkAuth(res: Response): void {
  if (res.status === 401) throw new AuthError()
}

export async function submitAssessment(req: AssessmentRequest): Promise<{ job_id: string }> {
  const res = await fetch(`${BASE}/assessments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(req),
  })
  checkAuth(res)
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export async function fetchJob(jobId: string): Promise<JobResponse> {
  const res = await fetch(`${BASE}/jobs/${jobId}`, { headers: authHeaders() })
  checkAuth(res)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchJobs(): Promise<JobSummary[]> {
  const res = await fetch(`${BASE}/jobs`, { headers: authHeaders() })
  checkAuth(res)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
