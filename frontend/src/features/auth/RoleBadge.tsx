import type { UserRole } from './types'

const ROLE_STYLES: Record<UserRole, string> = {
  admin: 'bg-amber-100 text-amber-900',
  manager: 'bg-forest-100 text-forest-900',
  viewer: 'bg-stone-200 text-stone-700',
}

export default function RoleBadge({ role }: { role: UserRole }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold capitalize ${ROLE_STYLES[role]}`}>
      {role}
    </span>
  )
}
