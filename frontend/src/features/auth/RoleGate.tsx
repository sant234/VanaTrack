import type { ReactNode } from 'react'

import type { UserRole } from './types'
import { useAuth } from './useAuth'

type RoleGateProps = {
  roles: UserRole[]
  children: ReactNode
  /** What to show instead when the role is not allowed (nothing by default). */
  fallback?: ReactNode
}

/**
 * Show children only to the listed roles, e.g. <RoleGate roles={['admin']}>…</RoleGate>.
 * This only hides UI. The backend still checks permissions on every request.
 */
export default function RoleGate({ roles, children, fallback = null }: RoleGateProps) {
  const { user } = useAuth()
  const isAllowed = user !== null && roles.includes(user.role)
  return <>{isAllowed ? children : fallback}</>
}
