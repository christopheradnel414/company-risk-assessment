import { useState } from 'react'
import type { AssessmentRequest } from '../types'

interface Props {
  onSubmit: (req: AssessmentRequest) => Promise<void>
}

export default function SubmitForm({ onSubmit }: Props) {
  const [companyName, setCompanyName] = useState('')
  const [regNumber, setRegNumber] = useState('')
  const [jurisdiction, setJurisdiction] = useState('GB')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!companyName.trim() && !regNumber.trim()) {
      setError('Provide at least a company name or registration number.')
      return
    }
    setError(null)
    setLoading(true)
    try {
      await onSubmit({
        company_name: companyName.trim() || undefined,
        registration_number: regNumber.trim() || undefined,
        jurisdiction: jurisdiction.trim().toUpperCase() || 'GB',
      })
      setCompanyName('')
      setRegNumber('')
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className="submit-form" onSubmit={handleSubmit}>
      <div className="submit-form-title">New Background Check</div>
      <div className="form-field">
        <label>Company Name</label>
        <input
          value={companyName}
          onChange={e => setCompanyName(e.target.value)}
          placeholder="Acme Consulting Ltd"
          disabled={loading}
        />
      </div>
      <div className="form-field">
        <label>Registration Number</label>
        <input
          value={regNumber}
          onChange={e => setRegNumber(e.target.value)}
          placeholder="12345678"
          disabled={loading}
        />
      </div>
      <div className="form-field">
        <label>Jurisdiction</label>
        <input
          value={jurisdiction}
          onChange={e => setJurisdiction(e.target.value.toUpperCase())}
          placeholder="GB"
          maxLength={2}
          disabled={loading}
        />
      </div>
      {error && <div className="form-error">{error}</div>}
      <button className="btn-submit" type="submit" disabled={loading}>
        {loading ? 'Submitting…' : 'Run Background Check'}
      </button>
    </form>
  )
}
