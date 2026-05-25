interface CHAddress {
  address_line_1?: string
  address_line_2?: string
  care_of?: string
  country?: string
  locality?: string
  po_box?: string
  postal_code?: string
  premises?: string
  region?: string
}

interface CHProfile {
  company_name?: string
  company_number?: string
  company_status?: string
  type?: string
  date_of_creation?: string
  date_of_cessation?: string
  has_been_liquidated?: boolean
  has_charges?: boolean
  has_insolvency_history?: boolean
  sic_codes?: string[]
  registered_office_address?: CHAddress
  previous_company_names?: Array<{ name: string; effective_from?: string; ceased_on?: string }>
  accounts?: {
    next_accounts?: { due_on?: string; overdue?: boolean }
    overdue?: boolean
  }
  confirmation_statement?: { next_due?: string; overdue?: boolean }
}

interface CHOfficer {
  name?: string
  officer_role?: string
  appointed_on?: string
  resigned_on?: string
  nationality?: string
}

interface CHPsc {
  name?: string
  nationality?: string
  ceased?: boolean
  ceased_on?: string
  is_sanctioned?: boolean
  natures_of_control?: string[]
}

interface CHFilingItem {
  category?: string
  date?: string
  description?: string
  type?: string
}

interface CompaniesHouseData {
  profile?: CHProfile
  officers?: { active_count?: number; resigned_count?: number; items?: CHOfficer[] }
  filing_history?: { total_count?: number; items?: CHFilingItem[] }
  persons_with_significant_control?: { active_count?: number; items?: CHPsc[] }
}

function fmtDate(d: string | null | undefined): string {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric' })
}

function fmtAddress(a: CHAddress | undefined): string {
  if (!a) return '—'
  return [a.premises, a.address_line_1, a.address_line_2, a.locality, a.region, a.country, a.postal_code]
    .filter(Boolean)
    .join(', ')
}

export default function CompaniesHouseView({ data }: { data: unknown }) {
  const d = data as CompaniesHouseData
  if (!d) return <p className="mv-empty">No data</p>

  const profile = d.profile
  const officers = d.officers
  const pscs = d.persons_with_significant_control
  const filings = d.filing_history

  const flags = [
    profile?.has_been_liquidated && 'Liquidated',
    profile?.has_insolvency_history && 'Insolvency history',
    profile?.has_charges && 'Has charges',
  ].filter(Boolean) as string[]

  return (
    <>
      {profile && (
        <div className="mv-section">
          <div className="mv-section-title">Company Profile</div>
          <div className="mv-grid-2">
            <div className="mv-field">
              <span className="mv-label">Status</span>
              <span className={`mv-status-chip ${profile.company_status?.toLowerCase().replace(/-/g, '_')}`}>
                {profile.company_status ?? '—'}
              </span>
            </div>
            <div className="mv-field">
              <span className="mv-label">Type</span>
              <span className="mv-value">{profile.type ?? '—'}</span>
            </div>
            <div className="mv-field">
              <span className="mv-label">Incorporated</span>
              <span className="mv-value">{fmtDate(profile.date_of_creation)}</span>
            </div>
            {profile.date_of_cessation && (
              <div className="mv-field">
                <span className="mv-label">Ceased</span>
                <span className="mv-value mv-danger">{fmtDate(profile.date_of_cessation)}</span>
              </div>
            )}
          </div>
          {profile.registered_office_address && (
            <div className="mv-field mv-field-block">
              <span className="mv-label">Registered address</span>
              <span className="mv-value">{fmtAddress(profile.registered_office_address)}</span>
            </div>
          )}
          {profile.sic_codes && profile.sic_codes.length > 0 && (
            <div className="mv-field mv-field-block">
              <span className="mv-label">SIC codes</span>
              <div className="mv-tags">
                {profile.sic_codes.map(c => <span key={c} className="mv-tag">{c}</span>)}
              </div>
            </div>
          )}
          {flags.length > 0 && (
            <div className="mv-flags">
              {flags.map(f => <span key={f} className="mv-flag">{f}</span>)}
            </div>
          )}
          {(profile.accounts?.overdue || profile.accounts?.next_accounts?.overdue) && (
            <span className="mv-alert">Accounts overdue</span>
          )}
          {profile.confirmation_statement?.overdue && (
            <span className="mv-alert">Confirmation statement overdue</span>
          )}
          {profile.previous_company_names && profile.previous_company_names.length > 0 && (
            <div className="mv-field mv-field-block">
              <span className="mv-label">Previous names</span>
              {profile.previous_company_names.map((n, i) => (
                <div key={i} className="mv-prev-name">
                  {n.name}
                  <span className="mv-prev-name-dates">
                    {' '}({fmtDate(n.effective_from)} – {n.ceased_on ? fmtDate(n.ceased_on) : 'present'})
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {officers && officers.items && officers.items.length > 0 && (
        <div className="mv-section">
          <div className="mv-section-title">
            Officers
            <span className="mv-count">{officers.active_count ?? 0} active · {officers.resigned_count ?? 0} resigned</span>
          </div>
          <div className="mv-table-wrap">
            <table className="mv-table">
              <thead>
                <tr><th>Name</th><th>Role</th><th>Appointed</th><th>Resigned</th></tr>
              </thead>
              <tbody>
                {officers.items.map((o, i) => (
                  <tr key={i} className={o.resigned_on ? 'mv-row-muted' : ''}>
                    <td>{o.name ?? '—'}</td>
                    <td>{o.officer_role ?? '—'}</td>
                    <td>{fmtDate(o.appointed_on)}</td>
                    <td>{o.resigned_on ? fmtDate(o.resigned_on) : <span className="mv-active">Active</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {pscs && pscs.items && pscs.items.length > 0 && (
        <div className="mv-section">
          <div className="mv-section-title">
            Persons with Significant Control
            <span className="mv-count">{pscs.active_count ?? 0} active</span>
          </div>
          {pscs.items.map((p, i) => (
            <div key={i} className={`mv-psc-row${p.ceased ? ' mv-row-muted' : ''}`}>
              <div className="mv-psc-name">
                {p.name ?? '—'}
                {p.is_sanctioned && <span className="mv-flag" style={{ marginLeft: 8 }}>Sanctioned</span>}
              </div>
              <div className="mv-psc-meta">
                {p.nationality && <span>{p.nationality}</span>}
                {p.ceased && <span>Ceased {fmtDate(p.ceased_on)}</span>}
              </div>
              {p.natures_of_control && p.natures_of_control.length > 0 && (
                <div className="mv-tags">
                  {p.natures_of_control.map((c, j) => <span key={j} className="mv-tag">{c}</span>)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {filings && filings.items && filings.items.length > 0 && (
        <div className="mv-section">
          <div className="mv-section-title">
            Recent Filings
            <span className="mv-count">{filings.total_count} total</span>
          </div>
          <div className="mv-filing-list">
            {filings.items.slice(0, 10).map((f, i) => (
              <div key={i} className="mv-filing-row">
                <span className="mv-filing-date">{fmtDate(f.date)}</span>
                <span className="mv-filing-cat" title={f.category}>{f.category}</span>
                <span className="mv-filing-desc">{f.description ?? f.type ?? '—'}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  )
}
