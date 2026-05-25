import { useState } from 'react'
import { getApiKey, setApiKey } from '../api'

export default function ApiKeySection() {
  const [key, setKey] = useState<string>(getApiKey)
  const [show, setShow] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    setKey(val)
    setApiKey(val)
  }

  const isSet = key.length > 0

  return (
    <div className="api-key-section">
      <div className="api-key-header">
        <span className="api-key-title">API Key</span>
        <span className={`api-key-status ${isSet ? 'set' : 'unset'}`}>
          {isSet ? 'set' : 'not set'}
        </span>
      </div>
      <div className="api-key-input-wrap">
        <input
          type={show ? 'text' : 'password'}
          value={key}
          onChange={handleChange}
          placeholder="Enter API key…"
          className="api-key-input"
          autoComplete="off"
          spellCheck={false}
        />
        <button
          type="button"
          className="api-key-toggle"
          onClick={() => setShow(s => !s)}
          title={show ? 'Hide key' : 'Show key'}
        >
          {show ? '🙈' : '👁'}
        </button>
      </div>
    </div>
  )
}
