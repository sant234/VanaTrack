import { MapPin } from 'lucide-react'
import { Link } from 'react-router-dom'

import { formatDate } from '../../lib/format'
import { BehindScheduleBadge, StatusBadge } from './ProjectBadges'
import ProjectProgressSummary from './ProjectProgressSummary'
import { TYPE_LABELS } from './projectLabels'
import type { Project } from './types'

/** One project as a tappable card (used on small screens). */
export default function ProjectCard({ project }: { project: Project }) {
  return (
    <Link
      to={`/projects/${project.id}`}
      className="block rounded-xl border border-stone-200 bg-white p-4 shadow-sm hover:border-forest-500 focus-visible:outline-2 focus-visible:outline-forest-500"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-semibold text-stone-900">{project.name}</p>
          <p className="mt-0.5 text-xs text-stone-500">{TYPE_LABELS[project.type]}</p>
        </div>
        <StatusBadge status={project.status} />
      </div>
      <p className="mt-2 flex items-center gap-1 text-sm text-stone-600">
        <MapPin aria-hidden className="size-4 shrink-0" />
        <span className="truncate">
          {project.district ? `${project.district}, ` : ''}
          {project.state}
        </span>
      </p>
      <div className="mt-3">
        <ProjectProgressSummary project={project} />
      </div>
      <div className="mt-2 flex items-center justify-between gap-2 text-xs text-stone-500">
        <span>Ends {formatDate(project.end_date)}</span>
        {project.is_behind_schedule && <BehindScheduleBadge />}
      </div>
    </Link>
  )
}
