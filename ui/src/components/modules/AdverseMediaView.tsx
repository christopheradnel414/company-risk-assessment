interface AdverseMediaHit {
  title: string
  url: string
  snippet: string
  category: string
}

interface AdverseMediaData {
  adverse_media_found: boolean
  summary: string
  hits: AdverseMediaHit[]
  risk_indicators?: string[]
}

export default function AdverseMediaView({ data }: { data: unknown }) {
  const d = data as AdverseMediaData
  if (!d) return <p className="mv-empty">No data</p>

  return (
    <>
      <div className={`mv-status-banner ${d.adverse_media_found ? 'danger' : 'clean'}`}>
        {d.adverse_media_found ? '⚠ Adverse media found' : '✓ No adverse media found'}
      </div>
      {d.summary && <p className="mv-summary">{d.summary}</p>}
      {d.hits && d.hits.length > 0 && (
        <div className="mv-section">
          <div className="mv-section-title">Adverse Media Hits ({d.hits.length})</div>
          {d.hits.map((h, i) => (
            <div key={i} className="mv-hit-card">
              <div className="mv-hit-header">
                <span className={`mv-category-badge ${h.category}`}>{h.category.replace(/_/g, ' ')}</span>
                <a href={h.url} target="_blank" rel="noreferrer" className="mv-hit-link">{h.title}</a>
              </div>
              <p className="mv-hit-snippet">{h.snippet}</p>
            </div>
          ))}
        </div>
      )}
    </>
  )
}
