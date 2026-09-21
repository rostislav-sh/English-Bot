import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import AttemptPage from './pages/AttemptPage'
import DashboardPage from './pages/DashboardPage'
import LoginPage from './pages/LoginPage'
import NotFoundPage from './pages/NotFoundPage'
import RegisterPage from './pages/RegisterPage'
import TestPage from './pages/TestPage'
import TopicsPage from './pages/TopicsPage'
import SimpleNav from './components/SimpleNav'
import { AuthProvider } from './auth/AuthContext'
import RequireAuth from './auth/RequireAuth'
import './App.css'

export default function App() {
	return (
		<BrowserRouter>
			<AuthProvider>
				<SimpleNav />
				<Routes>
					<Route path="/" element={<Navigate to="/dashboard" replace />} />
					<Route path="/login" element={<LoginPage />} />
					<Route path="/register" element={<RegisterPage />} />
					<Route
						path="/dashboard"
						element={
							<RequireAuth>
								<DashboardPage />
							</RequireAuth>
						}
					/>
					<Route
						path="/topics"
						element={
							<RequireAuth>
								<TopicsPage />
							</RequireAuth>
						}
					/>
					<Route
						path="/tests/:testId"
						element={
							<RequireAuth>
								<TestPage />
							</RequireAuth>
						}
					/>
					<Route
						path="/attempts/:attemptId"
						element={
							<RequireAuth>
								<AttemptPage />
							</RequireAuth>
						}
					/>
					<Route path="*" element={<NotFoundPage />} />
				</Routes>
			</AuthProvider>
		</BrowserRouter>
	)
}
