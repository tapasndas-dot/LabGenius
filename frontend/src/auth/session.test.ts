import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiRequest, setUnauthorizedHandler } from '../api/client'
import { authenticate } from './authApi'
import { loginSession, logoutSession, restoreSession } from './session'
import { tokenStorage } from './tokenStorage'

function memoryStorage(): Storage {
  const values = new Map<string, string>()
  return {
    get length() { return values.size },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => [...values.keys()][index] ?? null,
    removeItem: (key) => { values.delete(key) },
    setItem: (key, value) => { values.set(key, value) },
  }
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeEach(() => {
  Object.defineProperty(globalThis, 'window', {
    value: { localStorage: memoryStorage() }, configurable: true,
  })
  vi.restoreAllMocks()
  setUnauthorizedHandler(undefined)
})

describe('authentication API contract', () => {
  it('posts OAuth2 form data to the configured login endpoint', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      jsonResponse({ access_token: 'test-token', token_type: 'bearer' }),
    )

    await authenticate('analyst', 'test-password')

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/auth/login')
    expect(options?.method).toBe('POST')
    expect(options?.headers).toBeInstanceOf(Headers)
    expect((options?.headers as Headers).get('Content-Type')).toBe('application/x-www-form-urlencoded')
    expect(options?.body).toBeInstanceOf(URLSearchParams)
    expect((options?.body as URLSearchParams).get('username')).toBe('analyst')
    expect((options?.body as URLSearchParams).get('password')).toBe('test-password')
  })

  it('stores the token and loads the authenticated user after login', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({ access_token: 'stored-token', token_type: 'bearer' }))
      .mockResolvedValueOnce(jsonResponse({ id: '1', username: 'analyst', email: 'a@example.test', display_name: 'Analyst' }))

    const user = await loginSession('analyst', 'test-password')

    expect(user.display_name).toBe('Analyst')
    expect(tokenStorage.get()).toBe('stored-token')
  })
})

describe('session lifecycle and errors', () => {
  it('restores a user when a stored token is valid', async () => {
    tokenStorage.set('valid-token')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      jsonResponse({ id: '1', username: 'analyst', email: 'a@example.test', display_name: 'Analyst' }),
    )
    expect((await restoreSession())?.username).toBe('analyst')
  })

  it('clears an invalid stored token without retrying', async () => {
    tokenStorage.set('expired-token')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ detail: 'Invalid' }, 401))
    expect(await restoreSession()).toBeNull()
    expect(tokenStorage.get()).toBeNull()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('logout clears local authentication material', () => {
    tokenStorage.set('token')
    logoutSession()
    expect(tokenStorage.get()).toBeNull()
  })

  it('reports network failure safely', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('socket details'))
    await expect(authenticate('analyst', 'password')).rejects.toMatchObject({
      status: null,
      message: 'Unable to reach LabGenius. Check the server and try again.',
    })
  })

  it('does not discard a stored token during a temporary network failure', async () => {
    tokenStorage.set('stored-token')
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('offline'))
    expect(await restoreSession()).toBeNull()
    expect(tokenStorage.get()).toBe('stored-token')
  })

  it('does not clear authentication or invoke logout for 403', async () => {
    tokenStorage.set('valid-token')
    const unauthorized = vi.fn()
    setUnauthorizedHandler(unauthorized)
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ detail: 'Forbidden' }, 403))

    await expect(apiRequest('/restricted')).rejects.toBeInstanceOf(ApiError)
    expect(tokenStorage.get()).toBe('valid-token')
    expect(unauthorized).not.toHaveBeenCalled()
  })
})
