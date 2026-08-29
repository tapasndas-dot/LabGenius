// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'
import { AuthProvider } from '../auth/AuthContext'
import { hasPermission } from '../auth/useAuthorization'
import { tokenStorage } from '../auth/tokenStorage'

type UserOptions = { forced?: boolean; permissions?: string[] }

function user(options: UserOptions = {}) {
  return {
    id: '00000000-0000-0000-0000-000000000001',
    username: 'analyst', email: 'analyst@example.test', display_name: 'Lab Analyst',
    force_password_change: options.forced ?? false,
    permissions: options.permissions ?? [],
  }
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function renderRoute(path: string) {
  return render(<AuthProvider><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></AuthProvider>)
}

beforeEach(() => {
  window.localStorage.clear()
  vi.restoreAllMocks()
})

afterEach(cleanup)

describe('protected and forced-password routing', () => {
  it('redirects an unauthenticated user to login', async () => {
    renderRoute('/app')
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeTruthy()
  })

  it('keeps the loading screen while authentication initializes', () => {
    tokenStorage.set('stored-token')
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => undefined))
    renderRoute('/app')
    expect(screen.getByLabelText('Loading application')).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Welcome back' })).toBeNull()
  })

  it('allows an authenticated user into the application shell', async () => {
    tokenStorage.set('valid-token')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(user()))
    renderRoute('/app')
    expect(await screen.findByRole('heading', { name: 'Home' })).toBeTruthy()
    expect(screen.getByText('Lab Analyst')).toBeTruthy()
  })

  it('restricts a forced user to password change', async () => {
    tokenStorage.set('forced-token')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(user({ forced: true })))
    renderRoute('/app')
    expect(await screen.findByRole('heading', { name: 'Change your password' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Home' })).toBeNull()
  })

  it('redirects an authenticated user away from login', async () => {
    tokenStorage.set('valid-token')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(user()))
    renderRoute('/login')
    expect(await screen.findByRole('heading', { name: 'Home' })).toBeTruthy()
  })

  it('renders routing-level not found behavior', async () => {
    renderRoute('/missing-page')
    expect(await screen.findByRole('heading', { name: 'Page not found' })).toBeTruthy()
  })
})

describe('password change and authorization-aware navigation', () => {
  it('uses the backend password contract, refreshes me, and enters the app', async () => {
    tokenStorage.set('forced-token')
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse(user({ forced: true })))
      .mockResolvedValueOnce(jsonResponse({ message: 'Password changed successfully.' }))
      .mockResolvedValueOnce(jsonResponse(user({ forced: false })))
    renderRoute('/change-password')

    fireEvent.change(await screen.findByLabelText('Current password'), { target: { value: 'CurrentPass!42' } })
    fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'NewStrongPass!43' } })
    fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: 'NewStrongPass!43' } })
    fireEvent.click(screen.getByRole('button', { name: 'Change password' }))

    expect(await screen.findByRole('heading', { name: 'Home' })).toBeTruthy()
    const [url, request] = fetchMock.mock.calls[1]
    expect(url).toBe('/api/auth/change-password')
    expect(request?.method).toBe('POST')
    expect(JSON.parse(request?.body as string)).toEqual({
      current_password: 'CurrentPass!42', new_password: 'NewStrongPass!43',
      confirm_new_password: 'NewStrongPass!43',
    })
    expect(fetchMock.mock.calls[2][0]).toBe('/api/auth/me')
  })

  it('shows a safe password error and clears password inputs', async () => {
    tokenStorage.set('forced-token')
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse(user({ forced: true })))
      .mockResolvedValueOnce(jsonResponse({ detail: 'Current password is incorrect.' }, 422))
    renderRoute('/change-password')
    fireEvent.change(await screen.findByLabelText('Current password'), { target: { value: 'WrongPassword!42' } })
    fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'NewStrongPass!43' } })
    fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: 'NewStrongPass!43' } })
    fireEvent.click(screen.getByRole('button', { name: 'Change password' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Current password is incorrect.')
    expect((screen.getByLabelText('Current password') as HTMLInputElement).value).toBe('')
  })

  it('hides or shows Administration from effective permission codes', async () => {
    tokenStorage.set('valid-token')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(user()))
    const first = renderRoute('/app')
    await screen.findByRole('heading', { name: 'Home' })
    expect(screen.queryByRole('link', { name: 'Administration' })).toBeNull()
    first.unmount()

    fetchMock.mockResolvedValue(jsonResponse(user({ permissions: ['user.view'] })))
    renderRoute('/app')
    expect(await screen.findByRole('link', { name: 'Administration' })).toBeTruthy()
  })

  it('logout clears the session and returns to login', async () => {
    tokenStorage.set('valid-token')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(user()))
    renderRoute('/app')
    fireEvent.click(await screen.findByRole('button', { name: 'Sign out' }))
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeTruthy()
    expect(tokenStorage.get()).toBeNull()
  })

  it('permission helper is exact and conservative', () => {
    expect(hasPermission(['user.view'], 'user.view')).toBe(true)
    expect(hasPermission(['user.view'], 'user.update')).toBe(false)
  })
})
