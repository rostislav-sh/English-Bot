import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { ApiError } from '../api/http'
import { getMeProfile, login as loginRequest, logout as logoutRequest, register as registerRequest } from '../api/auth'
import { consumeCsrfFromUrl, getCsrfToken } from './csrfStorage'
import { onSessionExpired } from './authEvents'
import type { Authentication, RegisterIn, UserOut, UserProfileOut } from '../api/types/auth'
import { AuthContext } from './authContext.core'
import type { AuthContextValue } from './authContext.core'

const AUTH_USER_KEY = 'auth_user'

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

function userFromProfile(profile: UserProfileOut): UserOut {
	return { username: profile.username, email: profile.email }
}

function clearSession(
	setUser: (user: UserOut | null) => void,
	setUserId: (id: number | null) => void,
): void {
	setUser(null)
	setUserId(null)
	storeUser(null)
}

export function AuthProvider({ children }: { children: ReactNode }) {
	const [user, setUser] = useState<UserOut | null>(readStoredUser)
	const [userId, setUserId] = useState<number | null>(null)
	const [ready, setReady] = useState(false)

	const applyProfile = useCallback((profile: UserProfileOut): void => {
		const nextUser = userFromProfile(profile)
		storeUser(nextUser)
		setUser(nextUser)
		setUserId(profile.id)
	}, [])

	const reload = useCallback(async (): Promise<void> => {
		consumeCsrfFromUrl()
		getCsrfToken()
		try {
			const profile = await getMeProfile()
			applyProfile(profile)
		} catch (err) {
			const apiErr = err as ApiError
			if (apiErr.status === 401 || apiErr.status === 403) {
				clearSession(setUser, setUserId)
			}
		} finally {
			setReady(true)
		}
	}, [applyProfile])

	useEffect(() => {
		void reload()
	}, [reload])

	useEffect(
		() =>
			onSessionExpired(() => {
				clearSession(setUser, setUserId)
			}),
		[],
	)

	const login = useCallback(
		async (data: Authentication): Promise<void> => {
			const nextUser = await loginRequest(data)
			storeUser(nextUser)
			setUser(nextUser)
			try {
				const profile = await getMeProfile()
				applyProfile(profile)
			} catch {
				setUserId(null)
			}
		},
		[applyProfile],
	)

	const register = useCallback(
		async (data: RegisterIn): Promise<void> => {
			const nextUser = await registerRequest(data)
			storeUser(nextUser)
			setUser(nextUser)
			try {
				const profile = await getMeProfile()
				applyProfile(profile)
			} catch {
				setUserId(null)
			}
		},
		[applyProfile],
	)

	const logout = useCallback(async (): Promise<void> => {
		await logoutRequest()
		clearSession(setUser, setUserId)
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
