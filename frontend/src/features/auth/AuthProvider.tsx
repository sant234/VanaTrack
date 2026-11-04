/**
 * Holds "who is logged in" for the whole app.
 *
 * On page load: if a token was saved earlier, ask the API "who am I?" (/auth/me) to restore the session.
 * If the API later says the token is no longer valid (401), the user is logged out automatically.
 */
import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'

import { clearSavedToken, readSavedToken, saveToken, setUnauthorizedHandler } from '../../lib/api'
import { fetchCurrentUser, loginRequest, registerRequest } from './authApi'
import { AuthContext, type AuthContextValue, type AuthStatus } from './authContext'
import type { LoginInput, RegisterInput, User } from './types'

export default function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<AuthStatus>(() => (readSavedToken() ? 'loading' : 'anonymous'))
  const [sessionExpired, setSessionExpired] = useState(false)

  const endSession = useCallback(() => {
    clearSavedToken()
    setUser(null)
    setStatus('anonymous')
    // Forget all cached server data so the next user never sees the previous user's data.
    queryClient.clear()
  }, [queryClient])

  // Restore the session from a saved token, once, when the app starts.
  useEffect(() => {
    if (!readSavedToken()) return
    fetchCurrentUser()
      .then((currentUser) => {
        setUser(currentUser)
        setStatus('authenticated')
      })
      .catch(() => endSession())
  }, [endSession])

  // When any API call reports an ended session, log out and remember why.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      endSession()
      setSessionExpired(true)
    })
    return () => setUnauthorizedHandler(null)
  }, [endSession])

  const login = useCallback(async (input: LoginInput) => {
    const { access_token: token, user: loggedInUser } = await loginRequest(input)
    saveToken(token)
    setUser(loggedInUser)
    setStatus('authenticated')
    setSessionExpired(false)
    return loggedInUser
  }, [])

  // After creating the account, log straight in so the user doesn't have to type everything twice.
  const register = useCallback(
    async (input: RegisterInput) => {
      await registerRequest(input)
      return login({ email: input.email, password: input.password })
    },
    [login],
  )

  const logout = useCallback(() => {
    endSession()
    setSessionExpired(false)
  }, [endSession])

  const value = useMemo<AuthContextValue>(
    () => ({ user, status, sessionExpired, login, register, logout }),
    [user, status, sessionExpired, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
