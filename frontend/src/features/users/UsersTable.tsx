import { formatNumber, formatTimestampDate } from '../../lib/format'
import type { ManagedUser } from './types'
import { ActiveSwitch, RoleSelect, SELF_EXPLANATION, YouBadge, type UserControlsProps } from './UserControls'

type RowHandlers = Omit<UserControlsProps, 'user' | 'isSelf' | 'isSaving'>

/** All users as a table (used on large screens). */
export default function UsersTable({
  users,
  currentUserId,
  savingUserId,
  controlsFor,
}: {
  users: ManagedUser[]
  currentUserId: number
  savingUserId: number | null
  controlsFor: (user: ManagedUser) => RowHandlers
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-stone-200 bg-white shadow-sm">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-stone-200 bg-stone-50 text-xs font-semibold tracking-wide text-stone-500 uppercase">
          <tr>
            <th scope="col" className="px-4 py-3">User</th>
            <th scope="col" className="px-4 py-3">Role</th>
            <th scope="col" className="px-4 py-3">Status</th>
            <th scope="col" className="px-4 py-3">Projects owned</th>
            <th scope="col" className="px-4 py-3">Joined</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-100">
          {users.map((user) => {
            const props = {
              user,
              isSelf: user.id === currentUserId,
              isSaving: savingUserId === user.id,
              ...controlsFor(user),
            }
            return (
              <tr key={user.id} className={user.is_active ? '' : 'bg-stone-50 text-stone-500'}>
                <td className="px-4 py-3">
                  <p className="flex flex-wrap items-center gap-2 font-semibold text-stone-900">
                    {user.name}
                    {props.isSelf && <YouBadge />}
                  </p>
                  <p className="text-xs break-all text-stone-500">{user.email}</p>
                  {props.isSelf && <p className="mt-1 text-xs text-stone-500">{SELF_EXPLANATION}</p>}
                </td>
                <td className="px-4 py-3">
                  <RoleSelect {...props} />
                </td>
                <td className="px-4 py-3">
                  <ActiveSwitch {...props} />
                </td>
                <td className="px-4 py-3 text-stone-600">{formatNumber(user.owned_project_count)}</td>
                <td className="px-4 py-3 whitespace-nowrap text-stone-600">{formatTimestampDate(user.created_at)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
