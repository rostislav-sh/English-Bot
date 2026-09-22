const CSRF_STORAGE_KEY = 'csrf_token'
const CSRF_COOKIE_NAME: string =
	import.meta.env.VITE_CSRF_COOKIE_NAME ?? 'csrf_token'

let memoryToken: string | null = null

function readCookie(name: string): string | null {
	const prefix = `${encodeURIComponent(name)}=`
	const parts = document.cookie.split('; ')
	for (const part of parts) {
		if (part.startsWith(prefix) || part.startsWith(`${name}=`)) {
			const raw = part.slice(part.indexOf('=') + 1)
			try {
				return decodeURIComponent(raw)
			} catch {
				return raw
			}
		}
	}
	return null
}

export function setCsrfToken(token: string): void {
	memoryToken = token
	sessionStorage.setItem(CSRF_STORAGE_KEY, token)
}

export function clearCsrfToken(): void {
	memoryToken = null
	sessionStorage.removeItem(CSRF_STORAGE_KEY)
}

export function consumeCsrfFromUrl(): string | null {
	const url = new URL(window.location.href)
	const token = url.searchParams.get('csrf')
	if (!token) return null

	setCsrfToken(token)
	url.searchParams.delete('csrf')
	const next = `${url.pathname}${url.search}${url.hash}`
	window.history.replaceState({}, '', next)
	return token
}

export function getCsrfToken(): string | null {
	if (memoryToken) return memoryToken

	const stored = sessionStorage.getItem(CSRF_STORAGE_KEY)
	if (stored) {
		memoryToken = stored
		return stored
	}

	const fromCookie = readCookie(CSRF_COOKIE_NAME)
	if (fromCookie) {
		setCsrfToken(fromCookie)
		return fromCookie
	}

	return null
}
