import Badge, { type BadgeTone } from '../../components/Badge'
import type { UserRole } from './types'

const ROLE_TONES: Record<UserRole, BadgeTone> = {
  admin: 'warning',
  manager: 'success',
  viewer: 'neutral',
}

const ROLE_LABELS: Record<UserRole, string> = { admin: 'Admin', manager: 'Manager', viewer: 'Viewer' }

export default function RoleBadge({ role }: { role: UserRole }) {
  return <Badge tone={ROLE_TONES[role]}>{ROLE_LABELS[role]}</Badge>
}
