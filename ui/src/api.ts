import type { AssessmentRequest, JobResponse } from './types'

const BASE = '/api/v1'

export async function submitAssessment(req: AssessmentRequest): Promise<{ job_id: string }> {
  const res = await fetch(`${BASE}/assessments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export async function fetchJob(jobId: string): Promise<JobResponse> {
  const res = await fetch(`${BASE}/jobs/${jobId}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchJobs(): Promise<JobResponse[]> {
  const res = await fetch(`${BASE}/jobs`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
