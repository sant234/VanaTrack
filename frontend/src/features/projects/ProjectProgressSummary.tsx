import ProgressBar from '../../components/ProgressBar'
import { formatNumber, formatPercent } from '../../lib/format'
import type { Project } from './types'

/** "0 / 1,000 trees · 0%" with a bar underneath. Shared by the card, table and detail page. */
export default function ProjectProgressSummary({ project }: { project: Project }) {
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
        <span className="text-stone-600">
          {formatNumber(project.current_value)} / {formatNumber(project.target_value)} {project.unit}
        </span>
        <span className="font-semibold text-stone-900">{formatPercent(project.progress_percent)}</span>
      </div>
      <ProgressBar percent={project.progress_percent} label={`${project.name} progress`} />
    </div>
  )
}
