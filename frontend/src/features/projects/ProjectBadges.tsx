import { STATUS_LABELS } from './projectLabels'
import type { ProjectStatus } from './types'

const STATUS_STYLES: Record<ProjectStatus, string> = {
  planned: 'bg-sky-100 text-sky-900',
  active: 'bg-forest-100 text-forest-900',
  on_hold: 'bg-amber-100 text-amber-900',
  completed: 'bg-stone-800 text-white',
  cancelled: 'bg-stone-200 text-stone-600',
}

export function StatusBadge({ status }: { status: ProjectStatus }) {
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_STYLES[status]}`}>
      {STATUS_LABELS[status]}
    </span>
  )
}

export function BehindScheduleBadge() {
  return (
    <span className="inline-flex rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-800">
      Behind schedule
    </span>
  )
}
