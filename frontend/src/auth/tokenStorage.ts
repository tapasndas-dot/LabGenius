const ACCESS_TOKEN_KEY = 'labgenius.access_token'

export const tokenStorage = {
  get(): string | null {
    return window.localStorage.getItem(ACCESS_TOKEN_KEY)
  },

  set(token: string): void {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, token)
  },

  clear(): void {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY)
  },
}
