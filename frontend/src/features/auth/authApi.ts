import { apiRequest } from '../../lib/api'
import type { LoginInput, RegisterInput, TokenResponse, User } from './types'

export function loginRequest(input: LoginInput): Promise<TokenResponse> {
  return apiRequest<TokenResponse>('/auth/login', { method: 'POST', body: JSON.stringify(input) })
}

export function registerRequest(input: RegisterInput): Promise<User> {
  return apiRequest<User>('/auth/register', { method: 'POST', body: JSON.stringify(input) })
}

export function fetchCurrentUser(): Promise<User> {
  return apiRequest<User>('/auth/me')
}
