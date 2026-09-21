import { apiUrl } from './config'
import { clearCsrfToken, getCsrfToken, setCsrfToken } from '../auth/csrfStorage'

const CSRF_HEADER = 'X-CSRF-Token'

export class ApiError extends Error {
	status: number
	detail?: string

	constructor(status: number, message: string, detail?: string) {
		super(message)
		this.name = 'ApiError'
		this.status = status
		this.detail = detail
	}
}

type JsonValue =
	| null
	| boolean
	| number
	| string
	| JsonValue[]
	| { [key: string]: JsonValue }

type RequestOpts = {
	method: 'GET' | 'POST'
	body?: unknown
	skipAuthRetry?: boolean
}

function captureCsrf(response: Response): void {
	const token = response.headers.get(CSRF_HEADER)
	if (token) setCsrfToken(token)
}

function buildHeaders(opts: RequestOpts): Headers {
	const headers = new Headers()
	if (opts.body !== undefined) {
		headers.set('Content-Type', 'application/json')
	}
	const csrf = getCsrfToken()
	if (csrf) headers.set(CSRF_HEADER, csrf)
	return headers
}

function extractErrorDetail(json: JsonValue | undefined): string | undefined {
	if (!json || typeof json !== 'object' || Array.isArray(json)) return undefined
	const rec = json as { [key: string]: JsonValue }
	if (typeof rec.detail === 'string') return rec.detail
	if (typeof rec.message === 'string') return rec.message
	if (Array.isArray(rec.detail)) {
		const messages = rec.detail
			.map((item) => {
				if (item && typeof item === 'object' && !Array.isArray(item) && typeof item.msg === 'string') {
					return item.msg
				}
				return null
			})
			.filter((msg): msg is string => Boolean(msg))
		if (messages.length > 0) return messages.join('; ')
	}
	return undefined
}

async function parseJsonSafe(response: Response): Promise<JsonValue | undefined> {
	try {
		return (await response.json()) as JsonValue
	} catch {
		return undefined
	}
}

async function tryRefreshSession(): Promise<boolean> {
	const csrf = getCsrfToken()
	if (!csrf) return false

	const res = await fetch(apiUrl('/token/refresh'), {
		method: 'POST',
		credentials: 'include',
		headers: { [CSRF_HEADER]: csrf },
	})
	captureCsrf(res)
	return res.ok
}

export async function requestJson<TResponse>(
	path: string,
	opts: RequestOpts,
): Promise<TResponse> {
	let res: Response
	try {
		res = await fetch(apiUrl(path), {
			method: opts.method,
			credentials: 'include',
			headers: buildHeaders(opts),
			body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
			signal: AbortSignal.timeout(10000),
		})
	} catch (err) {
		throw new ApiError(
			0,
			'Network error',
			err instanceof Error ? err.message : 'Failed to reach API',
		)
	}

	captureCsrf(res)

	if (res.status === 401 && !opts.skipAuthRetry && path !== '/token/refresh') {
		const refreshed = await tryRefreshSession()
		if (refreshed) {
			return requestJson<TResponse>(path, { ...opts, skipAuthRetry: true })
		}
		clearCsrfToken()
	}

	if (!res.ok) {
		const json = await parseJsonSafe(res)
		throw new ApiError(
			res.status,
			`Request failed (${res.status})`,
			extractErrorDetail(json),
		)
	}

	if (res.status === 204) {
		return undefined as TResponse
	}

	return (await res.json()) as TResponse
}

export async function getJson<TResponse>(path: string): Promise<TResponse> {
	return requestJson<TResponse>(path, { method: 'GET' })
}

export async function postJson<TResponse, TBody = unknown>(
	path: string,
	body?: TBody,
): Promise<TResponse> {
	return requestJson<TResponse>(path, { method: 'POST', body })
}
