import type { JobResponse } from '../types'

interface Props {
  jobs: JobResponse[]
  selectedJobId: string | null
  onSelect: (id: string) => void
}

function relativeTime(iso: string): string {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  return `${Math.floor(m / 60)}h ago`
}

function jobDisplayName(job: JobResponse): string {
  // Prefer the resolved canonical name, then the original query, then the job ID
  const ctx = job.resolved_context ?? job.query
  return ctx.company_name ?? ctx.registration_number ?? job.job_id.slice(0, 8).toUpperCase()
}

function jobSubtitle(job: JobResponse): string {
  const ctx = job.resolved_context ?? job.query
  const parts = [ctx.jurisdiction, ctx.registration_number].filter(Boolean)
  return parts.join(' · ')
}

export default function JobList({ jobs, selectedJobId, onSelect }: Props) {
  return (
    <div className="job-list">
      <div className="job-list-label">Recent Jobs</div>
      {jobs.length === 0 && (
        <div className="job-list-empty">No jobs yet — submit one above.</div>
      )}
      {jobs.map(job => (
        <div
          key={job.job_id}
          className={`job-card${job.job_id === selectedJobId ? ' selected' : ''}`}
          onClick={() => onSelect(job.job_id)}
        >
          <div className="job-card-top">
            <span className="job-card-name">{jobDisplayName(job)}</span>
            <span className={`status-badge ${job.status}`}>{job.status}</span>
          </div>
          <div className="job-card-sub">{jobSubtitle(job)}</div>
          <div className="job-card-meta">
            <span className="job-card-time">{relativeTime(job.created_at)}</span>
            {job.progress.length > 0 && (
              <div className="job-card-modules">
                {job.progress.map(p => (
                  <span
                    key={p.module_id}
                    className={`module-dot ${p.status}`}
                    title={`${p.module_name}: ${p.status}`}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
