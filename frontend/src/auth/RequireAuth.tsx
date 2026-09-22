import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './useAuth'

export default function RequireAuth({ children }: { children: ReactNode }) {
	const { ready, isAuthenticated } = useAuth()
	const location = useLocation()

	if (!ready) {
		return (
			<main className="page">
				<p className="muted">Loading session...</p>
			</main>
		)
	}

	if (!isAuthenticated) {
		return <Navigate to="/login" replace state={{ from: location.pathname }} />
	}

	return children
}
