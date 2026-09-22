export type Authentication = {
	email: string
	password: string
}

export type RegisterIn = Authentication & {
	username: string
}

export type UserOut = {
	username: string | null
	email: string
}

export type UserProfileOut = {
	id: number
	email: string
	username: string | null
	created_at: string | null
}
