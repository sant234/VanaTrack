import { LoaderCircle } from 'lucide-react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from './useAuth'

/** Wrap private pages with this. Logged-out visitors go to /login, then come back here after logging in. */
export default function ProtectedRoute() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center" role="status">
        <LoaderCircle aria-hidden className="size-8 animate-spin text-forest-700" />
        <span className="sr-only">Loading your session…</span>
      </div>
    )
  }
  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  return <Outlet />
}
