export type Authentication = {
  email: string
  password: string
}

export type TokenPair = {
  access_token: string
  refresh_token: string
  token_type: string
}

export type RegisterOut = {
  id: number
  email: string
  access_token: string
  refresh_token: string
  token_type: string
}

export type RefreshRequest = {
  refresh_token: string
}

