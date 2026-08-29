export type AuthToken = {
  access_token: string
  token_type: string
}

export type CurrentUser = {
  id: string
  username: string
  email: string
  display_name: string
  // The backend does not currently return this from /auth/me. Keeping it
  // optional makes Task 15B routing ready when the contract is expanded.
  force_password_change?: boolean
}
