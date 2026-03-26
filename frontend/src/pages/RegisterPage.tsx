import type { FormEvent } from 'react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/http'
import { register, startGoogleOAuth } from '../api/auth'
import { saveTokens } from '../auth/tokenStorage'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setPending(true)
    try {
      const pair = await register({ email, password })
      saveTokens(pair)
      navigate('/dashboard')
    } catch (err) {
      const apiErr = err as ApiError
      setError(apiErr.detail ?? apiErr.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <main className="page">
      <h1>Register</h1>

      <form className="card" onSubmit={onSubmit}>
        <label className="field">
          <span>Email</span>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            required
            autoComplete="username"
          />
        </label>

        <label className="field">
          <span>Password</span>
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
          />
        </label>

        {error ? <div className="alert alert--error">{error}</div> : null}

        <button className="btn" type="submit" disabled={pending}>
          {pending ? 'Creating...' : 'Create account'}
        </button>

        <div className="divider">or</div>

        <button
          className="btn btn--secondary"
          type="button"
          onClick={() => startGoogleOAuth()}
        >
          Continue with Google
        </button>
      </form>
    </main>
  )
}

