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

export type MeOut = {
	user_id: number
}
