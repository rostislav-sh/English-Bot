import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { ApiError } from '../api/http'
import { getMe, login as loginRequest, logout as logoutRequest, register as registerRequest } from '../api/auth'
import { consumeCsrfFromUrl, getCsrfToken } from './csrfStorage'
import type { Authentication, RegisterIn, UserOut } from '../api/types/auth'

const AUTH_USER_KEY = 'auth_user'

type AuthContextValue = {
	user: UserOut | null
	userId: number | null
	ready: boolean
	isAuthenticated: boolean
	login: (data: Authentication) => Promise<void>
	register: (data: RegisterIn) => Promise<void>
	logout: () => Promise<void>
	reload: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function readStoredUser(): UserOut | null {
	const raw = sessionStorage.getItem(AUTH_USER_KEY)
	if (!raw) return null
	try {
		return JSON.parse(raw) as UserOut
	} catch {
		return null
	}
}

function storeUser(user: UserOut | null): void {
	if (!user) {
		sessionStorage.removeItem(AUTH_USER_KEY)
		return
	}
	sessionStorage.setItem(AUTH_USER_KEY, JSON.stringify(user))
}

export function AuthProvider({ children }: { children: ReactNode }) {
	const [user, setUser] = useState<UserOut | null>(readStoredUser)
	const [userId, setUserId] = useState<number | null>(null)
	const [ready, setReady] = useState(false)

	const reload = useCallback(async (): Promise<void> => {
		consumeCsrfFromUrl()
		getCsrfToken()
		try {
			const me = await getMe()
			setUserId(me.user_id)
			setUser((current) => current ?? readStoredUser())
		} catch (err) {
			const apiErr = err as ApiError
			if (apiErr.status === 401 || apiErr.status === 403) {
				setUserId(null)
				setUser(null)
				storeUser(null)
			}
		} finally {
			setReady(true)
		}
	}, [])

	useEffect(() => {
		void reload()
	}, [reload])

	const login = useCallback(async (data: Authentication): Promise<void> => {
		const nextUser = await loginRequest(data)
		storeUser(nextUser)
		setUser(nextUser)
		try {
			const me = await getMe()
			setUserId(me.user_id)
		} catch {
			setUserId(null)
		}
	}, [])

	const register = useCallback(async (data: RegisterIn): Promise<void> => {
		const nextUser = await registerRequest(data)
		storeUser(nextUser)
		setUser(nextUser)
		try {
			const me = await getMe()
			setUserId(me.user_id)
		} catch {
			setUserId(null)
		}
	}, [])

	const logout = useCallback(async (): Promise<void> => {
		await logoutRequest()
		setUser(null)
		setUserId(null)
		storeUser(null)
	}, [])

	const value = useMemo<AuthContextValue>(
		() => ({
			user,
			userId,
			ready,
			isAuthenticated: userId !== null || user !== null,
			login,
			register,
			logout,
			reload,
		}),
		[user, userId, ready, login, register, logout, reload],
	)

	return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
	const ctx = useContext(AuthContext)
	if (!ctx) {
		throw new Error('useAuth must be used within AuthProvider')
	}
	return ctx
}
