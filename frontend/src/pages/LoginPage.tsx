import type { FormEvent } from 'react'
import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/http'
import { startGoogleOAuth } from '../api/auth'
import { useAuth } from '../auth/AuthContext'
import GoogleIcon from '../components/GoogleIcon'

export default function LoginPage() {
	const navigate = useNavigate()
	const location = useLocation()
	const { login, isAuthenticated, ready } = useAuth()
	const [email, setEmail] = useState('')
	const [password, setPassword] = useState('')
	const [error, setError] = useState<string | null>(null)
	const [pending, setPending] = useState(false)

	const from =
		typeof location.state === 'object' &&
		location.state !== null &&
		'from' in location.state &&
		typeof location.state.from === 'string'
			? location.state.from
			: '/dashboard'

	async function onSubmit(e: FormEvent) {
		e.preventDefault()
		setError(null)
		setPending(true)
		try {
			await login({ email, password })
			navigate(from, { replace: true })
		} catch (err) {
			const apiErr = err as ApiError
			setError(apiErr.detail ?? apiErr.message)
		} finally {
			setPending(false)
		}
	}

	if (ready && isAuthenticated) {
		return <Navigate to={from} replace />
	}

	return (
		<main className="page">
			<h1>Login</h1>

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
						autoComplete="current-password"
					/>
				</label>

				{error ? <div className="alert alert--error" role="alert">{error}</div> : null}

				<button className="btn" type="submit" disabled={pending}>
					{pending ? 'Logging in...' : 'Login'}
				</button>

				<div className="divider">or</div>

				<button
					className="btn btn--secondary"
					type="button"
					onClick={() => startGoogleOAuth()}
				>
					<span className="btn__content">
						<GoogleIcon size={24} />
						<span>Continue with Google</span>
					</span>
				</button>
			</form>
		</main>
	)
}
