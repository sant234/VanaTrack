import { useContext } from 'react'

import { AuthContext, type AuthContextValue } from './authContext'

/** Read the logged-in user and the login/logout actions from anywhere inside <AuthProvider>. */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside <AuthProvider>')
  }
  return context
}
