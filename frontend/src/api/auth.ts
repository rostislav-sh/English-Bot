import { apiUrl } from './config'
import { getJson, postJson } from './http'
import { clearCsrfToken } from '../auth/csrfStorage'
import type { Authentication, ProfileOut, RegisterIn, UserOut } from './types/auth'

export async function register(data: RegisterIn): Promise<UserOut> {
	return postJson<UserOut, RegisterIn>('/register', data)
}

export async function login(data: Authentication): Promise<UserOut> {
	return postJson<UserOut, Authentication>('/login', data)
}

export async function refresh(): Promise<{ message: string }> {
	return postJson<{ message: string }>('/token/refresh')
}

export async function logout(): Promise<void> {
	try {
		await postJson<{ message: string }>('/logout')
	} finally {
		clearCsrfToken()
		sessionStorage.removeItem('auth_user')
	}
}

export async function getMeProfile(): Promise<ProfileOut> {
	return getJson<ProfileOut>('/me/profile')
}

export function startGoogleOAuth(): void {
	window.location.assign(apiUrl('/auth/google'))
}

export function readGoogleCallbackErrorFromUrl(): string | null {
	const params = new URLSearchParams(window.location.search)
	return params.get('auth_error')
}
