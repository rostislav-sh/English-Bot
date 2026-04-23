import { apiUrl } from './config';

export class ApiError extends Error {
	status: number;
	detail?: string;

	constructor(status: number, message: string, detail?: string) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
		this.detail = detail;
	}
}

type JsonValue =
	| null
	| boolean
	| number
	| string
	| JsonValue[]
	| { [key: string]: JsonValue };

async function parseJsonSafe(
	response: Response,
): Promise<JsonValue | undefined> {
	try {
		return (await response.json()) as JsonValue;
	} catch {
		return undefined;
	}
}

export async function requestJson<TResponse>(
	path: string,
	opts: { method: 'GET' | 'POST'; body?: unknown },
): Promise<TResponse> {
	const res = await fetch(apiUrl(path), {
		method: opts.method,

		credentials: 'include',
		headers:
			opts.body !== undefined
				? { 'Content-Type': 'application/json' }
				: undefined,
		body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
	});

	if (!res.ok) {
		const json = await parseJsonSafe(res);
		const detail = (json as Record<string, unknown>)?.detail;
		throw new ApiError(
			res.status,
			`Request failed (${res.status})`,
			typeof detail === 'string' ? detail : undefined,
		);
	}

	return (await res.json()) as TResponse;
}

export async function getJson<TResponse>(path: string): Promise<TResponse> {
	return requestJson<TResponse>(path, { method: 'GET' });
}

export async function postJson<TResponse, TBody>(
	path: string,
	body: TBody,
): Promise<TResponse> {
	return requestJson<TResponse>(path, { method: 'POST', body });
}
