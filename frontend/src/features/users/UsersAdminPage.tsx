/**
 * /users (admins only): change roles and activate or deactivate accounts.
 * Deactivating asks for confirmation first, because it signs the person out on their next request.
 * The backend is the real guard: it refuses non-admins (403) and changes to the admin's own account (400).
 */
import { Users } from 'lucide-react'
import { useState } from 'react'

import Alert from '../../components/Alert'
import ConfirmDialog from '../../components/ConfirmDialog'
import Skeleton from '../../components/Skeleton'
import { EmptyState, ErrorState } from '../../components/StatePanels'
import { ApiError } from '../../lib/api'
import type { UserRole } from '../auth/types'
import { useAuth } from '../auth/useAuth'
import type { ManagedUser, UserChanges } from './types'
import UserCard from './UserCard'
import UsersTable from './UsersTable'
import { useUpdateUser, useUsers } from './useUsers'

function successMessage(user: ManagedUser, changes: UserChanges): string {
  if (changes.role) return `${user.name} is now a ${changes.role}.`
  return changes.is_active ? `${user.name} was reactivated.` : `${user.name} was deactivated.`
}

export default function UsersAdminPage() {
  const { user: currentUser } = useAuth()
  const users = useUsers()
  const updateUser = useUpdateUser()
  const [userToDeactivate, setUserToDeactivate] = useState<ManagedUser | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const savingUserId = updateUser.isPending ? (updateUser.variables?.userId ?? null) : null

  async function save(user: ManagedUser, changes: UserChanges) {
    setNotice(null)
    try {
      await updateUser.mutateAsync({ userId: user.id, changes })
      setNotice(successMessage(user, changes))
    } catch {
      // The error is shown above the list from updateUser.error.
    }
  }

  function controlsFor(user: ManagedUser) {
    return {
      onRoleChange: (role: UserRole) => void save(user, { role }),
      onActiveChange: (isActive: boolean) =>
        isActive ? void save(user, { is_active: true }) : setUserToDeactivate(user),
    }
  }

  async function confirmDeactivate() {
    if (!userToDeactivate) return
    await save(userToDeactivate, { is_active: false })
    setUserToDeactivate(null)
  }

  function renderBody() {
    if (users.isPending) {
      return (
        <div className="space-y-3" role="status" aria-label="Loading users">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      )
    }
    if (users.isError) return <ErrorState message={users.error.message} onRetry={() => void users.refetch()} />
    if (users.data.length === 0) {
      return <EmptyState icon={Users} title="No users yet" description="People who register will appear here." />
    }
    const currentUserId = currentUser?.id ?? -1
    return (
      <>
        <ul className="space-y-3 lg:hidden">
          {users.data.map((user) => (
            <li key={user.id}>
              <UserCard
                user={user}
                isSelf={user.id === currentUserId}
                isSaving={savingUserId === user.id}
                {...controlsFor(user)}
              />
            </li>
          ))}
        </ul>
        <div className="hidden lg:block">
          <UsersTable
            users={users.data}
            currentUserId={currentUserId}
            savingUserId={savingUserId}
            controlsFor={controlsFor}
          />
        </div>
      </>
    )
  }

  return (
    <section className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-stone-900">Users</h1>
        <p className="mt-1 text-sm text-stone-500">
          Change roles or deactivate accounts. A change applies to that person's very next request.
        </p>
      </div>

      {updateUser.isError && (
        <Alert>{updateUser.error instanceof ApiError ? updateUser.error.message : 'Could not update the user.'}</Alert>
      )}
      {notice && <Alert tone="info">{notice}</Alert>}

      {renderBody()}

      <ConfirmDialog
        open={userToDeactivate !== null}
        title="Deactivate this user?"
        confirmLabel="Deactivate"
        isConfirming={updateUser.isPending}
        onConfirm={() => void confirmDeactivate()}
        onCancel={() => setUserToDeactivate(null)}
      >
        {userToDeactivate && (
          <p>
            {userToDeactivate.name} ({userToDeactivate.email}) will be signed out and cannot log in until an admin
            reactivates the account. Their projects stay as they are.
          </p>
        )}
      </ConfirmDialog>
    </section>
  )
}
