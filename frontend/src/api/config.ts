export const API_BASE_URL: string =
	import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export function apiUrl(path: string): string {
	const base = API_BASE_URL.replace(/\/$/, '');
	const normalizedPath = path.startsWith('/') ? path : `/${path}`;
	return `${base}${normalizedPath}`;
}
