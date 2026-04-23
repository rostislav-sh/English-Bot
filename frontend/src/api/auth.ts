import { apiUrl } from './config';
import { getJson, postJson } from './http';
import type {
	Authentication,
	RefreshRequest,
	RegisterOut,
	TokenPair,
} from './types/auth';

export async function register(data: Authentication): Promise<RegisterOut> {
	return postJson<RegisterOut, Authentication>('/register', data);
}

export async function login(data: Authentication): Promise<TokenPair> {
	return postJson<TokenPair, Authentication>('/login', data);
}

export async function refresh(data: RefreshRequest): Promise<TokenPair> {
	return postJson<TokenPair, RefreshRequest>('/token/refresh', data);
}

export function startGoogleOAuth(): void {
	window.location.assign(apiUrl('/auth/google'));
}

export function navigateToGoogleCallback(args: {
	code?: string;
	state?: string;
	error?: string;
}): void {
	const url = new URL(apiUrl('/auth/google/callback'));
	if (args.code) url.searchParams.set('code', args.code);
	if (args.state) url.searchParams.set('state', args.state);
	if (args.error) url.searchParams.set('error', args.error);
	window.location.assign(url.toString());
}

export function readGoogleCallbackErrorFromUrl(): string | null {
	const params = new URLSearchParams(window.location.search);
	return params.get('auth_error');
}

export async function health(): Promise<{ status: string }> {
	return getJson<{ status: string }>('/health');
}
