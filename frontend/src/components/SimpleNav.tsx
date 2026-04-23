import { Link } from 'react-router-dom'
import { clearTokens } from '../auth/tokenStorage'
import { useNavigate } from 'react-router-dom'

export default function SimpleNav() {
  const navigate = useNavigate()

  function handleLogout() {
    clearTokens()
    navigate('/login')
  }

  return (
    <header className="topbar">
      <div className="topbar__brand">
        <strong>English Bot</strong>
      </div>
      <nav className="topbar__nav">
        <Link to="/login">Login</Link>
        <Link to="/register">Register</Link>
        <Link to="/dashboard">Dashboard</Link>
        <button type="button" className="topbar__logout" onClick={handleLogout}>
          Logout
        </button>
      </nav>
    </header>
  )
}

