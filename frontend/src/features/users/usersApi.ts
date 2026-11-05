import { apiRequest } from '../../lib/api'
import type { ManagedUser, UserChanges } from './types'

/** Admins only. Sorted by name. */
export function fetchUsers(): Promise<ManagedUser[]> {
  return apiRequest<ManagedUser[]>('/users')
}

/** Admins only. The server refuses changes to the admin's own role or active status. */
export function updateUser(userId: number, changes: UserChanges): Promise<ManagedUser> {
  return apiRequest<ManagedUser>(`/users/${userId}`, { method: 'PATCH', body: JSON.stringify(changes) })
}
