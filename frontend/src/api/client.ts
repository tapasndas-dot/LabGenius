import { tokenStorage } from '../auth/tokenStorage'
import { API_BASE_URL } from './config'

type ApiErrorBody = {
  detail?: string | Array<{ loc?: Array<string | number>; msg?: string }>
}

export class ApiError extends Error {
  readonly status: number | null

  constructor(
    message: string,
    status: number | null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: BodyInit | Record<string, unknown>
  authenticated?: boolean
}

let unauthorizedHandler: (() => void) | undefined

export function setUnauthorizedHandler(handler?: () => void): void {
  unauthorizedHandler = handler
}

async function parseError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as ApiErrorBody
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) {
      const messages = body.detail.map((item) => item.msg).filter(Boolean)
      if (messages.length) return messages.join(' ')
    }
    return 'Request failed.'
  } catch {
    return 'Request failed.'
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { authenticated = true, body, headers: initialHeaders, ...requestInit } = options
  const headers = new Headers(initialHeaders)
  const token = authenticated ? tokenStorage.get() : null

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  let requestBody = body
  if (body && !(body instanceof URLSearchParams) && !(body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
    requestBody = JSON.stringify(body)
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...requestInit,
      headers,
      body: requestBody as BodyInit | undefined,
    })
  } catch {
    throw new ApiError('Unable to reach LabGenius. Check the server and try again.', null)
  }

  if (!response.ok) {
    if (response.status === 401 && token) {
      tokenStorage.clear()
      unauthorizedHandler?.()
    }
    throw new ApiError(await parseError(response), response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}
