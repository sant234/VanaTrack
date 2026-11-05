import { formatNumber, formatTimestampDate } from '../../lib/format'
import { ActiveSwitch, RoleSelect, SELF_EXPLANATION, YouBadge, type UserControlsProps } from './UserControls'

/** One user as a card with the same controls as the table (used on small screens). */
export default function UserCard(props: UserControlsProps) {
  const { user, isSelf } = props
  return (
    <div
      className={`rounded-xl border border-stone-200 p-4 shadow-sm ${user.is_active ? 'bg-white' : 'bg-stone-50'}`}
    >
      <p className="flex flex-wrap items-center gap-2 font-semibold break-words text-stone-900">
        {user.name}
        {isSelf && <YouBadge />}
      </p>
      <p className="text-sm break-all text-stone-500">{user.email}</p>
      <p className="mt-1 text-xs text-stone-500">
        Owns {formatNumber(user.owned_project_count)} {user.owned_project_count === 1 ? 'project' : 'projects'} ·
        Joined {formatTimestampDate(user.created_at)}
      </p>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <RoleSelect {...props} />
        <ActiveSwitch {...props} />
      </div>
      {isSelf && <p className="mt-2 text-xs text-stone-500">{SELF_EXPLANATION}</p>}
    </div>
  )
}
