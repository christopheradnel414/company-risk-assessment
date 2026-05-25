import type { JobResponse } from '../types'

interface Props {
  jobs: JobResponse[]
  jobCache: Record<string, JobResponse>
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

function jobDisplayName(job: JobResponse, cache: Record<string, JobResponse>): string {
  const full = cache[job.job_id]
  return full?.final_assessment_result?.company_name ?? job.job_id.slice(0, 8).toUpperCase()
}

export default function JobList({ jobs, jobCache, selectedJobId, onSelect }: Props) {
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
            <span className="job-card-name">{jobDisplayName(job, jobCache)}</span>
            <span className={`status-badge ${job.status}`}>{job.status}</span>
          </div>
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
