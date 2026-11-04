import { createContext } from 'react'

import type { LoginInput, RegisterInput, User } from './types'

/** loading = checking a saved token on page load; anonymous = not logged in. */
export type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

export type AuthContextValue = {
  user: User | null
  status: AuthStatus
  /** True when the user was logged out because their session expired or was revoked. */
  sessionExpired: boolean
  login: (input: LoginInput) => Promise<User>
  register: (input: RegisterInput) => Promise<User>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
