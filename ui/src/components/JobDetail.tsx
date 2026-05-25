import { useState } from 'react'
import type { AssessmentResult, CandidateCompany, JobResponse, SearchResult } from '../types'

interface Props {
  job: JobResponse
  onSelectCandidate: (candidate: CandidateCompany) => Promise<void>
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`status-badge ${status}`}>{status}</span>
}

function ModuleResultCard({ result }: { result: SearchResult }) {
  const [open, setOpen] = useState(true)

  return (
    <div className="module-result">
      <div className="module-result-header" onClick={() => setOpen(o => !o)}>
        <span className={`module-dot ${result.status}`} />
        <span className="module-result-name">{result.module_name}</span>
        <StatusBadge status={result.status} />
        <span className={`chevron${open ? ' open' : ''}`}>▼</span>
      </div>
      {open && (
        <div className="module-result-body">
          {result.error ? (
            <div className="module-error-box">{result.error}</div>
          ) : result.data != null ? (
            <pre className="json-viewer">{JSON.stringify(result.data, null, 2)}</pre>
          ) : (
            <span style={{ fontSize: 13, color: 'var(--text-light)' }}>No data</span>
          )}
          {result.schema_errors && result.schema_errors.length > 0 && (
            <div className="schema-warnings">
              <div className="schema-warnings-title">Schema warnings:</div>
              {result.schema_errors.map((e, i) => <div key={i}>{e}</div>)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function RiskPanel({ result }: { result: AssessmentResult }) {
  const { risk_summary, company_name, registration_number, jurisdiction, warnings } = result
  const level = risk_summary.overall_risk_level

  return (
    <>
      <div className="risk-panel">
        <div className={`risk-score-circle ${level}`}>
          <span className="risk-score-number">{risk_summary.risk_score}</span>
          <span className="risk-score-sub">/100</span>
        </div>
        <div className="risk-info">
          <div className={`risk-level-badge ${level}`}>{level} risk</div>
          <p className="risk-summary-text">{risk_summary.summary}</p>
        </div>
      </div>
      {(warnings.length > 0 || company_name || registration_number) && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header">Company Details</div>
          <div className="card-body">
            {company_name && (
              <div style={{ fontSize: 13, marginBottom: 4 }}>
                <span style={{ color: 'var(--text-muted)', marginRight: 6 }}>Name</span>
                <strong>{company_name}</strong>
              </div>
            )}
            {registration_number && (
              <div style={{ fontSize: 13, marginBottom: 4 }}>
                <span style={{ color: 'var(--text-muted)', marginRight: 6 }}>Number</span>
                <code style={{ fontFamily: 'monospace' }}>{registration_number}</code>
              </div>
            )}
            <div style={{ fontSize: 13, marginBottom: warnings.length > 0 ? 10 : 0 }}>
              <span style={{ color: 'var(--text-muted)', marginRight: 6 }}>Jurisdiction</span>
              <strong>{jurisdiction}</strong>
            </div>
            {warnings.length > 0 && (
              <ul className="warnings-list">
                {warnings.map((w, i) => <li key={i}><span>⚠</span>{w}</li>)}
              </ul>
            )}
          </div>
        </div>
      )}
    </>
  )
}

function CandidatePicker({
  candidates,
  onSelect,
}: {
  candidates: CandidateCompany[]
  onSelect: (c: CandidateCompany) => Promise<void>
}) {
  const [selectingId, setSelectingId] = useState<string | null>(null)

  const handle = async (c: CandidateCompany) => {
    setSelectingId(c.registration_number)
    try {
      await onSelect(c)
    } finally {
      setSelectingId(null)
    }
  }

  return (
    <div className="candidate-banner">
      <div className="candidate-banner-title">⚠ Multiple companies found</div>
      <p className="candidate-banner-sub">
        The registry returned {candidates.length} matches. Select the correct company to continue.
      </p>
      {candidates.map(c => (
        <div key={c.registration_number} className="candidate-row">
          <div className="candidate-info">
            <div className="candidate-name">{c.company_name}</div>
            <div className="candidate-sub">{c.registration_number} · {c.jurisdiction} · {c.source}</div>
            {c.company_status && (
              <span className="candidate-status-chip">{c.company_status}</span>
            )}
            {c.warnings.length > 0 && (
              <div className="candidate-warnings">{c.warnings.join(' ')}</div>
            )}
          </div>
          <button
            className="btn-select"
            onClick={() => handle(c)}
            disabled={selectingId !== null}
          >
            {selectingId === c.registration_number ? '…' : 'Select'}
          </button>
        </div>
      ))}
    </div>
  )
}

function durationSeconds(start: string | null, end: string | null): string | null {
  if (!start || !end) return null
  const s = (new Date(end).getTime() - new Date(start).getTime()) / 1000
  return `${s.toFixed(1)}s`
}

export default function JobDetail({ job, onSelectCandidate }: Props) {
  const assessment = job.final_assessment_result
  const title = assessment?.company_name
    ?? job.candidates?.[0]?.company_name
    ?? `Job ${job.job_id.slice(0, 8).toUpperCase()}`

  const metaParts = [
    assessment?.jurisdiction ?? job.candidates?.[0]?.jurisdiction,
    assessment?.registration_number,
  ].filter(Boolean)

  return (
    <div className="job-detail">
      {/* Header */}
      <div className="job-detail-header">
        <div className="job-detail-title">
          <h1>{title}</h1>
          {metaParts.length > 0 && (
            <div className="job-detail-meta">{metaParts.join(' · ')}</div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          {(job.status === 'pending' || job.status === 'running') && (
            <span className="spinner" />
          )}
          <StatusBadge status={job.status} />
        </div>
      </div>

      {/* Failed */}
      {job.status === 'failed' && job.error && (
        <div className="failed-banner">
          <div className="failed-banner-title">Assessment Failed</div>
          <p className="failed-banner-msg">{job.error}</p>
        </div>
      )}

      {/* Ambiguous */}
      {job.status === 'ambiguous' && job.candidates && job.candidates.length > 0 && (
        <CandidatePicker candidates={job.candidates} onSelect={onSelectCandidate} />
      )}

      {/* Risk summary */}
      {assessment && <RiskPanel result={assessment} />}

      {/* Module progress */}
      {job.progress.length > 0 && (
        <div className="card">
          <div className="card-header">
            Module Progress
            {job.status === 'running' && <span className="spinner" style={{ marginLeft: 'auto' }} />}
          </div>
          <div className="card-body-flush">
            {job.progress.map(p => (
              <div key={p.module_id} className="module-row">
                <span className={`module-dot ${p.status}`} style={{ width: 9, height: 9 }} />
                <span className="module-row-name">{p.module_name}</span>
                <StatusBadge status={p.status} />
                {p.error && (
                  <span className="module-row-error" title={p.error}>{p.error}</span>
                )}
                <span className="module-row-dur">
                  {durationSeconds(p.started_at, p.completed_at)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Module results (live as they finish) */}
      {job.finished_module_results.length > 0 && (
        <div className="card">
          <div className="card-header">Module Results</div>
          <div className="card-body-flush">
            {job.finished_module_results.map(r => (
              <ModuleResultCard key={r.module_id} result={r} />
            ))}
          </div>
        </div>
      )}

      {/* Full JSON */}
      <div className="card">
        <div className="card-header">Full Response JSON</div>
        <div className="card-body">
          <pre className="json-viewer">{JSON.stringify(job, null, 2)}</pre>
        </div>
      </div>
    </div>
  )
}
