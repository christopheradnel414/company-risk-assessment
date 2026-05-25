interface ICIJEntity {
  name: string
  dataset: string
  entity_type: string
  score: number
  match?: boolean
  source_url?: string
}

interface ICIJData {
  is_mentioned_in_leaks: boolean
  entities_found: ICIJEntity[]
  summary: string
}

export default function ICIJLeaksView({ data }: { data: unknown }) {
  const d = data as ICIJData
  if (!d) return <p className="mv-empty">No data</p>

  return (
    <>
      <div className={`mv-status-banner ${d.is_mentioned_in_leaks ? 'danger' : 'clean'}`}>
        {d.is_mentioned_in_leaks ? '⚠ Mentioned in leak datasets' : '✓ Not found in leak datasets'}
      </div>
      {d.summary && <p className="mv-summary">{d.summary}</p>}
      {d.entities_found && d.entities_found.length > 0 && (
        <div className="mv-section">
          <div className="mv-section-title">Matching Entities ({d.entities_found.length})</div>
          {d.entities_found.map((e, i) => (
            <div key={i} className="mv-entity-row">
              <div className="mv-entity-header">
                <span className="mv-entity-name">{e.name}</span>
                <span className="mv-dataset-badge">{e.dataset}</span>
                {e.match && <span className="mv-match-badge">Match</span>}
              </div>
              <div className="mv-entity-meta">
                <span className="mv-entity-type">{e.entity_type}</span>
                <span className="mv-entity-score">Score: {e.score.toFixed(0)}</span>
                {e.source_url && (
                  <a href={e.source_url} target="_blank" rel="noreferrer" className="mv-link">
                    View in database ↗
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}
