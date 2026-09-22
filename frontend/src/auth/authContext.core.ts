import { createContext } from 'react'
import type { Authentication, RegisterIn, UserOut } from '../api/types/auth'

export type AuthContextValue = {
	user: UserOut | null
	userId: number | null
	ready: boolean
	isAuthenticated: boolean
	login: (data: Authentication) => Promise<void>
	register: (data: RegisterIn) => Promise<void>
	logout: () => Promise<void>
	reload: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
