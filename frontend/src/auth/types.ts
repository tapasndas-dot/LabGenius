export type AuthToken = {
  access_token: string
  token_type: string
}

export type CurrentUser = {
  id: string
  username: string
  email: string
  display_name: string
  force_password_change: boolean
  permissions: string[]
}
