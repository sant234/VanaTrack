import Badge, { type BadgeTone } from '../../components/Badge'
import { STATUS_LABELS } from './projectLabels'
import type { ProjectStatus } from './types'

const STATUS_TONES: Record<ProjectStatus, BadgeTone> = {
  planned: 'info',
  active: 'success',
  on_hold: 'warning',
  completed: 'strong',
  cancelled: 'muted',
}

export function StatusBadge({ status }: { status: ProjectStatus }) {
  return <Badge tone={STATUS_TONES[status]}>{STATUS_LABELS[status]}</Badge>
}

export function BehindScheduleBadge() {
  return <Badge tone="danger">Behind schedule</Badge>
}

export function TargetExceededBadge() {
  return <Badge tone="success">Exceeded target</Badge>
}
