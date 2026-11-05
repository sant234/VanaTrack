import type { UserRole } from '../auth/types'

/** One row of the Users page, as returned by GET /api/users. */
export type ManagedUser = {
  id: number
  name: string
  email: string
  role: UserRole
  is_active: boolean
  created_at: string
  owned_project_count: number
}

/** What PATCH /api/users/{id} accepts: send only what changes. */
export type UserChanges = {
  role?: UserRole
  is_active?: boolean
}
