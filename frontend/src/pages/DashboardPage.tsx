import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ApiError } from '../api/http'
import { refresh } from '../api/auth'
import { getMonthlyStats, listAttempts } from '../api/quiz'
import { useAuth } from '../auth/useAuth'
import StatsChart from '../components/StatsChart'
import type { AttemptHistoryItemOut, MonthlyStatOut } from '../api/types/quiz'

function errorMessageFromGoogleAuthError(authError: string | null): string | null {
	if (!authError) return null
	switch (authError) {
		case 'google_cancelled':
			return 'Google login was cancelled.'
		case 'csrf_mismatch':
			return 'Google login failed (CSRF state mismatch). Please try again.'
		case 'google_auth_failed':
			return 'Google authentication failed.'
		default:
			return `Google login error: ${authError}`
	}
}

function formatDate(value: string | null): string {
	if (!value) return '—'
	const date = new Date(value)
	if (Number.isNaN(date.getTime())) return value
	return date.toLocaleString()
}

export default function DashboardPage() {
	const location = useLocation()
	const { user, reload } = useAuth()
	const [pending, setPending] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [lastAction, setLastAction] = useState<string | null>(null)
	const [history, setHistory] = useState<AttemptHistoryItemOut[]>([])
	const [stats, setStats] = useState<MonthlyStatOut[]>([])
	const [loadingQuiz, setLoadingQuiz] = useState(true)

	const googleAuthError = useMemo(() => {
		const params = new URLSearchParams(location.search)
		return errorMessageFromGoogleAuthError(params.get('auth_error'))
	}, [location.search])

	useEffect(() => {
		let cancelled = false
		setLoadingQuiz(true)
		Promise.all([listAttempts(), getMonthlyStats()])
			.then(([attempts, monthly]) => {
				if (cancelled) return
				setHistory(attempts)
				setStats(monthly)
			})
			.catch((err: unknown) => {
				if (cancelled) return
				const apiErr = err as ApiError
				setError(apiErr.detail ?? apiErr.message)
			})
			.finally(() => {
				if (!cancelled) setLoadingQuiz(false)
			})
		return () => {
			cancelled = true
		}
	}, [])

	async function handleRefresh() {
		setError(null)
		setPending(true)
		try {
			await refresh()
			await reload()
			setLastAction('Session refreshed successfully.')
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

			<section className="card card--wide">
				<h2 className="card__title">Account</h2>
				<p className="muted">You are signed in. Tokens live in httpOnly cookies, not in localStorage.</p>
				<div className="kv">
					<div className="kv__row">
						<span>Username</span>
						<code>{user?.username ?? '—'}</code>
					</div>
					<div className="kv__row">
						<span>Email</span>
						<code>{user?.email ?? '—'}</code>
					</div>
				</div>

				{error ? <div className="alert alert--error">{error}</div> : null}
				{lastAction ? <div className="alert alert--success">{lastAction}</div> : null}

				<div className="actions">
					<Link className="btn" to="/topics">
						Start a quiz
					</Link>
					<button className="btn btn--secondary" type="button" disabled={pending} onClick={() => void handleRefresh()}>
						{pending ? 'Refreshing...' : 'Refresh session'}
					</button>
				</div>
			</section>

			<section className="card card--wide">
				<h2 className="card__title">Monthly stats</h2>
				{loadingQuiz ? <p className="muted">Loading stats...</p> : null}
				{!loadingQuiz && stats.length === 0 ? <p className="muted">No attempts this period yet.</p> : null}
				{!loadingQuiz && stats.length > 0 ? <StatsChart stats={stats} /> : null}
			</section>

			<section className="card card--wide">
				<h2 className="card__title">Recent attempts</h2>
				{loadingQuiz ? <p className="muted">Loading history...</p> : null}
				{!loadingQuiz && history.length === 0 ? <p className="muted">No quiz attempts yet.</p> : null}
				<ul className="history-list">
					{history.map((item) => (
						<li key={item.id}>
							<Link to={`/attempts/${item.id}`}>
								<span>
									{item.score}/{item.total_questions} · {Math.round(item.percentage)}%
								</span>
								<span className="muted">{formatDate(item.created_at)}</span>
							</Link>
						</li>
					))}
				</ul>
			</section>
		</main>
	)
}
