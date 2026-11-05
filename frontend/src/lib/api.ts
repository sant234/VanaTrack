/**
 * The one place the frontend talks to the backend.
 *
 * - Prefixes every path with VITE_API_URL.
 * - Attaches the saved login token as "Authorization: Bearer <token>".
 * - Turns any failed response into an ApiError with the backend's {detail, code, fields}.
 * - When a logged-in request gets 401 (expired or revoked session), calls the unauthorized handler.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'

const TOKEN_STORAGE_KEY = 'vanatrack_token'

/** Status code used when the request never reached the server (offline, server down, CORS). */
const NETWORK_ERROR_STATUS = 0
const UNAUTHORIZED_STATUS = 401

let unauthorizedHandler: (() => void) | null = null

/** Register what to do when the session stops being valid (the auth provider logs the user out). */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler
}

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

// Storage can be blocked (e.g. some private-browsing modes). Then we simply behave as "not logged in".
export function readSavedToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

export function saveToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
  } catch {
    // Not saved: the user stays logged in until the page is reloaded.
  }
}

export function clearSavedToken(): void {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
  } catch {
    // Nothing stored, nothing to clear.
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  const body = (await response.json().catch(() => ({}))) as ErrorBody
  const detail = typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`
  const code = typeof body.code === 'string' ? body.code : 'UNKNOWN_ERROR'
  const fields = body.fields && typeof body.fields === 'object' ? (body.fields as FieldErrors) : {}
  return new ApiError(response.status, code, detail, fields)
}

/** Send a request with the saved token. Returns the successful response, or throws an ApiError. */
async function send(path: string, options: RequestInit): Promise<Response> {
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
    // Only a request that carried a token means "your session ended". A 401 from the login form
    // (wrong password) has no token and is just shown as a normal form error.
    if (response.status === UNAUTHORIZED_STATUS && token) {
      unauthorizedHandler?.()
    }
    throw await toApiError(response)
  }
  return response
}

/** Call the API and return the parsed JSON, or throw an ApiError. */
export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await send(path, options)
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

/** The file name the server suggested in Content-Disposition, e.g. attachment; filename="x.csv". */
function filenameFrom(response: Response, fallback: string): string {
  const match = /filename="([^"]+)"/.exec(response.headers.get('Content-Disposition') ?? '')
  return match ? match[1] : fallback
}

/**
 * Download a file that needs the login token. A plain <a href> cannot send the Authorization header,
 * so the file is fetched here, turned into a Blob, and saved through a temporary object URL.
 */
export async function apiDownload(path: string, fallbackFilename: string): Promise<void> {
  const response = await send(path, {})
  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filenameFrom(response, fallbackFilename)
  document.body.append(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
}
