import { useContext } from 'react'
import { AuthContext } from './authContext.core'
import type { AuthContextValue } from './authContext.core'

export function useAuth(): AuthContextValue {
	const ctx = useContext(AuthContext)
	if (!ctx) {
		throw new Error('useAuth must be used within AuthProvider')
	}
	return ctx
}
