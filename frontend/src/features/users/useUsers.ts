/**
 * Data hooks for user management.
 *
 * A role or status change also invalidates "activity" (it writes a log entry) and "projects"
 * (a demoted owner loses edit rights, which changes each project's can_edit flag).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import type { UserChanges } from './types'
import { fetchUsers, updateUser } from './usersApi'

export const userKeys = {
  all: ['users'] as const,
}

export function useUsers() {
  return useQuery({ queryKey: userKeys.all, queryFn: fetchUsers })
}

export function useUpdateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, changes }: { userId: number; changes: UserChanges }) => updateUser(userId, changes),
    onSuccess: () =>
      Promise.all(
        [userKeys.all, ['activity'], ['projects']].map((queryKey) => queryClient.invalidateQueries({ queryKey })),
      ),
  })
}
