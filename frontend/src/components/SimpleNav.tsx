import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function SimpleNav() {
	const navigate = useNavigate()
	const { isAuthenticated, logout, ready } = useAuth()

	async function handleLogout() {
		await logout()
		navigate('/login')
	}

	return (
		<header className="topbar">
			<div className="topbar__brand">
				<strong>English Bot</strong>
			</div>
			<nav className="topbar__nav">
				{isAuthenticated ? (
					<>
						<Link to="/dashboard">Dashboard</Link>
						<Link to="/topics">Quizzes</Link>
						<button type="button" className="topbar__logout" onClick={() => void handleLogout()}>
							Logout
						</button>
					</>
				) : (
					<>
						<Link to="/login">Login</Link>
						<Link to="/register">Register</Link>
						{ready ? <Link to="/dashboard">Dashboard</Link> : null}
					</>
				)}
			</nav>
		</header>
	)
}
