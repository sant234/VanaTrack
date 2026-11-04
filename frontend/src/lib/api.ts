/**
 * The one place the frontend talks to the backend.
 *
 * - Prefixes every path with VITE_API_URL.
 * - Attaches the login token when one is saved (used from Prompt 1).
 * - Turns any failed response into an ApiError with the backend's {detail, code, fields}.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'

export const TOKEN_STORAGE_KEY = 'vanatrack_token'

/** Status code used when the request never reached the server (offline, server down, CORS). */
const NETWORK_ERROR_STATUS = 0

export type FieldErrors = Record<string, string>

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly fields: FieldErrors

  constructor(status: number, code: string, detail: string, fields: FieldErrors = {}) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fields = fields
  }
}

type ErrorBody = { detail?: unknown; code?: unknown; fields?: unknown }

function readSavedToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY)
  } catch {
    // Storage can be blocked (e.g. private mode). Treat that as "not logged in".
    return null
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  const body = (await response.json().catch(() => ({}))) as ErrorBody
  const detail = typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`
  const code = typeof body.code === 'string' ? body.code : 'UNKNOWN_ERROR'
  const fields = body.fields && typeof body.fields === 'object' ? (body.fields as FieldErrors) : {}
  return new ApiError(response.status, code, detail, fields)
}

/** Call the API and return the parsed JSON, or throw an ApiError. */
export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const token = readSavedToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
  } catch {
    throw new ApiError(NETWORK_ERROR_STATUS, 'NETWORK_ERROR', 'Cannot reach the server. Is the API running?')
  }

  if (!response.ok) {
    throw await toApiError(response)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}
