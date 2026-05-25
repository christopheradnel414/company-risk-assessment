import { useRef, useState } from 'react'
import type { AssessmentResult, CandidateCompany, JobResponse, SearchContext, SearchResult } from '../types'
import { ModuleView } from './ModuleViews'

interface Props {
  job: JobResponse
  onSelectCandidate: (candidate: CandidateCompany) => Promise<void>
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`status-badge ${status}`}>{status}</span>
}

function ModuleResultCard({ result }: { result: SearchResult }) {
  const [open, setOpen] = useState(true)
  const [rawOpen, setRawOpen] = useState(false)

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
            <>
              <ModuleView moduleId={result.module_id} data={result.data} />
              <div className="mv-raw-toggle">
                <button className="mv-raw-btn" onClick={() => setRawOpen(o => !o)}>
                  {rawOpen ? 'Hide raw JSON' : 'View raw JSON'}
                </button>
                {rawOpen && (
                  <pre className="json-viewer mv-raw-json">{JSON.stringify(result.data, null, 2)}</pre>
                )}
              </div>
            </>
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

function normalise(s: string | null | undefined): string {
  return (s ?? '').toLowerCase().trim()
}

function contextMismatch(query: SearchContext, resolved: SearchContext): string[] {
  const warnings: string[] = []
  if (
    query.company_name &&
    resolved.company_name &&
    normalise(query.company_name) !== normalise(resolved.company_name)
  ) {
    warnings.push(
      `Searched for "${query.company_name}" but registry resolved to "${resolved.company_name}".`
    )
  }
  if (
    query.registration_number &&
    resolved.registration_number &&
    normalise(query.registration_number) !== normalise(resolved.registration_number)
  ) {
    warnings.push(
      `Registration number changed from "${query.registration_number}" to "${resolved.registration_number}".`
    )
  }
  return warnings
}

function ContextPanel({ query, resolved }: { query: SearchContext; resolved: SearchContext | null }) {
  const mismatches = resolved ? contextMismatch(query, resolved) : []
  const showResolved = resolved && (
    normalise(query.company_name) !== normalise(resolved.company_name) ||
    normalise(query.registration_number) !== normalise(resolved.registration_number)
  )

  if (mismatches.length === 0 && !showResolved) return null

  return (
    <div className="context-panel">
      {mismatches.map((w, i) => (
        <div key={i} className="context-mismatch-row">
          <span className="context-mismatch-icon">⚠</span>
          <span>{w}</span>
        </div>
      ))}
      {showResolved && resolved && (
        <div className="context-resolved-row">
          <span className="context-resolved-label">Resolved to</span>
          <span className="context-resolved-value">
            {[resolved.company_name, resolved.registration_number, resolved.jurisdiction]
              .filter(Boolean)
              .join(' · ')}
          </span>
        </div>
      )}
    </div>
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
  const dialogRef = useRef<HTMLDialogElement>(null)

  const assessment = job.final_assessment_result
  const ctx = job.resolved_context ?? job.query
  const title = ctx.company_name ?? ctx.registration_number ?? `Job ${job.job_id.slice(0, 8).toUpperCase()}`
  const metaParts = [ctx.jurisdiction, ctx.registration_number].filter(Boolean)

  // True while the job is queued but no module has started yet
  const isQueued = job.status === 'pending' && job.progress.length === 0 && !assessment

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
        <div className="job-detail-header-right">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {(job.status === 'pending' || job.status === 'running') && (
              <span className="spinner" />
            )}
            <StatusBadge status={job.status} />
          </div>
          <button className="btn-view-json-inline" onClick={() => dialogRef.current?.showModal()}>
            {'{ }'} View JSON
          </button>
        </div>
      </div>

      {/* Queued state — show instead of the main body */}
      {isQueued && (
        <div className="job-queued-body">
          <span className="spinner job-queued-spinner" />
          <div className="job-queued-text">Job submitted — waiting for processing to start</div>
          <p className="job-queued-sub">Search modules will begin shortly. This page updates automatically.</p>
        </div>
      )}

      {!isQueued && (
        <>
          {/* Full-width alerts */}
          <ContextPanel query={job.query} resolved={job.resolved_context} />

          {job.status === 'failed' && job.error && (
            <div className="failed-banner">
              <div className="failed-banner-title">Assessment Failed</div>
              <p className="failed-banner-msg">{job.error}</p>
            </div>
          )}

          {job.status === 'ambiguous' && job.candidates && job.candidates.length > 0 && (
            <CandidatePicker candidates={job.candidates} onSelect={onSelectCandidate} />
          )}
        </>
      )}

      {/* Two-column body */}
      {!isQueued && (
        <div className="job-detail-grid">
          {/* Left: risk summary + module progress */}
          <div className="job-detail-left">
            {assessment && <RiskPanel result={assessment} />}

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
          </div>

          {/* Right: module results + JSON button */}
          <div className="job-detail-right">
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

          </div>
        </div>
      )}

      {/* Full JSON dialog */}
      <dialog
        ref={dialogRef}
        className="json-dialog"
        onClick={e => { if (e.target === dialogRef.current) dialogRef.current?.close() }}
      >
        <div className="json-dialog-header">
          <span>Full Response JSON</span>
          <button className="json-dialog-close" onClick={() => dialogRef.current?.close()}>✕</button>
        </div>
        <div className="json-dialog-body">
          <pre className="json-viewer">{JSON.stringify(job, null, 2)}</pre>
        </div>
      </dialog>
    </div>
  )
}
