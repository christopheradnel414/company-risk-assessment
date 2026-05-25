import { useMemo, useState } from 'react'
import type { JobResponse } from '../types'

interface Props {
  jobs: JobResponse[]
  selectedJobId: string | null
  onSelect: (id: string) => void
}

type SortKey = 'newest' | 'oldest' | 'status'

const STATUS_ORDER: Record<string, number> = { running: 0, pending: 1, ambiguous: 2, failed: 3, completed: 4 }

function relativeTime(iso: string): string {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  return `${Math.floor(m / 60)}h ago`
}

function jobDisplayName(job: JobResponse): string {
  const ctx = job.resolved_context ?? job.query
  return ctx.company_name ?? ctx.registration_number ?? job.job_id.slice(0, 8).toUpperCase()
}

function jobSubtitle(job: JobResponse): string {
  const ctx = job.resolved_context ?? job.query
  return [ctx.jurisdiction, ctx.registration_number].filter(Boolean).join(' · ')
}

export default function JobList({ jobs, selectedJobId, onSelect }: Props) {
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<SortKey>('newest')

  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim()
    let list = jobs

    if (q) {
      list = list.filter(job => {
        const ctx = job.resolved_context ?? job.query
        return (
          ctx.company_name?.toLowerCase().includes(q) ||
          ctx.registration_number?.toLowerCase().includes(q) ||
          ctx.jurisdiction?.toLowerCase().includes(q)
        )
      })
    }

    switch (sort) {
      case 'newest':
        return [...list].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      case 'oldest':
        return [...list].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
      case 'status':
        return [...list].sort((a, b) => (STATUS_ORDER[a.status] ?? 5) - (STATUS_ORDER[b.status] ?? 5))
    }
  }, [jobs, query, sort])

  return (
    <div className="job-list">
      <div className="job-list-controls">
        <div className="job-list-label">Recent Jobs</div>
        <div className="job-filter">
          <input
            type="text"
            className="job-filter-input"
            placeholder="Filter by name or number…"
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
          {query && (
            <button className="job-filter-clear" onClick={() => setQuery('')}>✕</button>
          )}
        </div>
        <div className="job-sort">
          {(['newest', 'oldest', 'status'] as SortKey[]).map(s => (
            <button
              key={s}
              className={`job-sort-btn${sort === s ? ' active' : ''}`}
              onClick={() => setSort(s)}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="job-cards">
        {filtered.length === 0 && (
          <div className="job-list-empty">
            {query ? 'No jobs match your filter.' : 'No jobs yet — submit one above.'}
          </div>
        )}
        {filtered.map(job => (
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
    </div>
  )
}
