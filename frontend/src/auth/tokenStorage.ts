import type { TokenPair } from '../api/types/auth'

const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const TOKEN_TYPE_KEY = 'token_type'

export type StoredTokens = {
  access_token: string
  refresh_token: string
  token_type: string
}

export function saveTokens(pair: TokenPair): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, pair.access_token)
  localStorage.setItem(REFRESH_TOKEN_KEY, pair.refresh_token)
  localStorage.setItem(TOKEN_TYPE_KEY, pair.token_type ?? 'bearer')
}

export function loadTokens(): StoredTokens | null {
  const access_token = localStorage.getItem(ACCESS_TOKEN_KEY)
  const refresh_token = localStorage.getItem(REFRESH_TOKEN_KEY)
  const token_type = localStorage.getItem(TOKEN_TYPE_KEY) ?? 'bearer'

  if (!access_token || !refresh_token) return null
  return { access_token, refresh_token, token_type }
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(TOKEN_TYPE_KEY)
}

