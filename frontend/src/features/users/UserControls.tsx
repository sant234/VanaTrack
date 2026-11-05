/** The role dropdown and the active/inactive switch for one user, shared by the table and the cards. */
import Badge from '../../components/Badge'
import SelectField from '../../components/SelectField'
import type { UserRole } from '../auth/types'
import type { ManagedUser } from './types'

const ROLE_OPTIONS: { value: UserRole; label: string }[] = [
  { value: 'admin', label: 'Admin' },
  { value: 'manager', label: 'Manager' },
  { value: 'viewer', label: 'Viewer' },
]

export const SELF_EXPLANATION = 'This is you. Another admin must change your role or status.'

/** Marks the logged-in admin's own row. */
export function YouBadge() {
  return <Badge tone="info">You</Badge>
}

export type UserControlsProps = {
  user: ManagedUser
  /** The logged-in admin's own row: the server refuses self-changes, so the controls are off. */
  isSelf: boolean
  isSaving: boolean
  onRoleChange: (role: UserRole) => void
  onActiveChange: (isActive: boolean) => void
}

export function RoleSelect({ user, isSelf, isSaving, onRoleChange }: UserControlsProps) {
  return (
    <SelectField
      label={`Role for ${user.name}`}
      hideLabel
      options={ROLE_OPTIONS}
      value={user.role}
      disabled={isSelf || isSaving}
      title={isSelf ? SELF_EXPLANATION : undefined}
      onChange={(event) => onRoleChange(event.target.value as UserRole)}
      className="w-36"
    />
  )
}

export function ActiveSwitch({ user, isSelf, isSaving, onActiveChange }: UserControlsProps) {
  const isOn = user.is_active
  return (
    <button
      type="button"
      role="switch"
      aria-checked={isOn}
      aria-label={`${user.name} is ${isOn ? 'active' : 'inactive'}`}
      disabled={isSelf || isSaving}
      title={isSelf ? SELF_EXPLANATION : undefined}
      onClick={() => onActiveChange(!isOn)}
      className="inline-flex min-h-10 items-center gap-2 rounded-lg text-sm font-medium text-stone-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forest-500 disabled:cursor-not-allowed disabled:opacity-60"
    >
      <span
        aria-hidden
        className={`relative inline-flex h-6 w-11 shrink-0 rounded-full transition-colors ${isOn ? 'bg-forest-500' : 'bg-stone-300'}`}
      >
        <span
          className={`absolute top-0.5 size-5 rounded-full bg-white shadow transition-transform ${isOn ? 'translate-x-5' : 'translate-x-0.5'}`}
        />
      </span>
      {isOn ? 'Active' : 'Inactive'}
    </button>
  )
}
