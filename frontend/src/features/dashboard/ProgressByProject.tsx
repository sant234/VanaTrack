/** The ten projects with the most progress, each bar coloured AND labelled by its state. */
import { Link } from 'react-router-dom'

import { formatPercent } from '../../lib/format'
import type { Project } from '../projects/types'
import BarRow from './BarRow'
import { PROGRESS_STATE_STYLE, type ProgressState } from './chartColors'

const TOP_COUNT = 10

function stateOf(project: Project): ProgressState {
  if (project.is_target_exceeded) return 'exceeded'
  if (project.is_behind_schedule) return 'behind'
  return 'on_track'
}

export default function ProgressByProject({ projects }: { projects: Project[] }) {
  const shown = projects.filter((project) => project.status !== 'cancelled').slice(0, TOP_COUNT)
  if (shown.length === 0) return <p className="text-sm text-stone-500">No projects to show.</p>

  return (
    <>
      <ul aria-label="Legend" className="mb-4 flex flex-wrap gap-x-4 gap-y-1 text-xs text-stone-600">
        {Object.values(PROGRESS_STATE_STYLE).map(({ bar, label }) => (
          <li key={label} className="flex items-center gap-1.5">
            <span aria-hidden className={`size-2.5 rounded-full ${bar}`} />
            {label}
          </li>
        ))}
      </ul>
      <ol className="space-y-3">
        {shown.map((project) => {
          const style = PROGRESS_STATE_STYLE[stateOf(project)]
          return (
            <BarRow
              key={project.id}
              percent={project.progress_percent}
              barClass={style.bar}
              label={
                <Link to={`/projects/${project.id}`} className="font-medium hover:text-forest-700 hover:underline">
                  {project.name}
                </Link>
              }
              value={
                <>
                  <span className="font-semibold text-stone-900">{formatPercent(project.progress_percent)}</span> ·{' '}
                  {style.label}
                </>
              }
            />
          )
        })}
      </ol>
    </>
  )
}
