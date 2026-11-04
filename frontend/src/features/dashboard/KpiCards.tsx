import { AlertTriangle, Award, FolderKanban, Gauge, Leaf, Wind, type LucideIcon } from 'lucide-react'

import { formatNumber, formatPercent } from '../../lib/format'
import type { DashboardSummary } from './types'

type Tile = { label: string; value: string; detail: string; icon: LucideIcon; highlight?: boolean }

function tilesFor(summary: DashboardSummary): Tile[] {
  return [
    {
      label: 'Projects',
      value: formatNumber(summary.total_projects),
      detail: `${formatNumber(summary.active_projects)} active`,
      icon: FolderKanban,
    },
    {
      label: 'Average completion',
      value: formatPercent(summary.average_completion_percent),
      detail: `Across ${summary.completion_project_count} started, non-cancelled ${summary.completion_project_count === 1 ? 'project' : 'projects'}`,
      icon: Gauge,
    },
    {
      label: 'Trees planted',
      value: formatNumber(summary.trees_planted),
      detail: 'Projects measured in trees',
      icon: Leaf,
    },
    {
      label: 'CO₂ absorbed (estimate)',
      value: `${formatNumber(summary.estimated_co2_tonnes_per_year)} t/yr`,
      detail: `Assumes ${summary.co2_kg_per_tree_per_year} kg per tree per year`,
      icon: Wind,
    },
    {
      label: 'Behind schedule',
      value: formatNumber(summary.behind_schedule_count),
      detail: 'Active, >10 points behind the timeline',
      icon: AlertTriangle,
      highlight: summary.behind_schedule_count > 0,
    },
    {
      label: 'Exceeded target',
      value: formatNumber(summary.exceeded_target_count),
      detail: 'Current total above target',
      icon: Award,
    },
  ]
}

export default function KpiCards({ summary }: { summary: DashboardSummary }) {
  return (
    <ul aria-label="Key figures" className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
      {tilesFor(summary).map(({ label, value, detail, icon: Icon, highlight }) => (
        <li
          key={label}
          className={`rounded-2xl border bg-white p-4 ${highlight ? 'border-red-200' : 'border-stone-200'}`}
        >
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm text-stone-600">{label}</p>
            <Icon aria-hidden className={`size-4 shrink-0 ${highlight ? 'text-red-600' : 'text-stone-400'}`} />
          </div>
          <p className="mt-2 text-2xl font-semibold text-stone-900">{value}</p>
          <p className="mt-1 text-xs text-stone-500">{detail}</p>
        </li>
      ))}
    </ul>
  )
}
