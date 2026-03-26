import { useMemo, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ApiError } from '../api/http'
import { refresh } from '../api/auth'
import { loadTokens, saveTokens } from '../auth/tokenStorage'

function errorMessageFromGoogleAuthError(auth_error: string | null): string | null {
  if (!auth_error) return null
  switch (auth_error) {
    case 'google_cancelled':
      return 'Google login was cancelled.'
    case 'csrf_mismatch':
      return 'Google login failed (CSRF state mismatch). Please try again.'
    case 'google_auth_failed':
      return 'Google authentication failed.'
    default:
      return `Google login error: ${auth_error}`
  }
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastAction, setLastAction] = useState<string | null>(null)

  const googleAuthError = useMemo(() => {
    const params = new URLSearchParams(location.search)
    return errorMessageFromGoogleAuthError(params.get('auth_error'))
  }, [location.search])

  const storedTokens = useMemo(() => loadTokens(), [])
  const hasRefresh = Boolean(storedTokens?.refresh_token)

  async function handleRefresh() {
    setError(null)
    setPending(true)
    try {
      if (!storedTokens?.refresh_token) {
        setError('No refresh token found in localStorage. Please login again.')
        return
      }
      const pair = await refresh({ refresh_token: storedTokens.refresh_token })
      saveTokens(pair)
      setLastAction('Tokens refreshed successfully.')
    } catch (err) {
      const apiErr = err as ApiError
      setError(apiErr.detail ?? apiErr.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <main className="page">
      <h1>Dashboard</h1>

      {googleAuthError ? <div className="alert alert--info">{googleAuthError}</div> : null}

      <section className="card">
        <h2 className="card__title">Auth status</h2>

        <p className="muted">
          {storedTokens ? 'You have tokens stored in localStorage.' : 'You are not logged in.'}
        </p>

        {storedTokens ? (
          <div className="kv">
            <div className="kv__row">
              <span>Access token</span>
              <code>{storedTokens.access_token.slice(0, 16)}...</code>
            </div>
            <div className="kv__row">
              <span>Refresh token</span>
              <code>{storedTokens.refresh_token.slice(0, 16)}...</code>
            </div>
          </div>
        ) : null}

        {error ? <div className="alert alert--error">{error}</div> : null}
        {lastAction ? <div className="alert alert--success">{lastAction}</div> : null}

        <div className="actions">
          <button className="btn" type="button" disabled={pending || !hasRefresh} onClick={handleRefresh}>
            {pending ? 'Refreshing...' : 'Refresh tokens'}
          </button>
          <button className="btn btn--secondary" type="button" onClick={() => navigate('/login')}>
            Go to login
          </button>
        </div>
      </section>
    </main>
  )
}

