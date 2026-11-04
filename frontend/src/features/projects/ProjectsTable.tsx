import { Link } from 'react-router-dom'

import { formatDate } from '../../lib/format'
import { BehindScheduleBadge, StatusBadge } from './ProjectBadges'
import ProjectProgressSummary from './ProjectProgressSummary'
import { TYPE_LABELS } from './projectLabels'
import type { Project } from './types'

/** All projects as a table (used on medium screens and up). */
export default function ProjectsTable({ projects }: { projects: Project[] }) {
  return (
    <div className="overflow-hidden rounded-xl border border-stone-200 bg-white shadow-sm">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-stone-200 bg-stone-50 text-xs font-semibold tracking-wide text-stone-500 uppercase">
          <tr>
            <th scope="col" className="px-4 py-3">Project</th>
            <th scope="col" className="px-4 py-3">Location</th>
            <th scope="col" className="px-4 py-3">Status</th>
            <th scope="col" className="w-64 px-4 py-3">Progress</th>
            <th scope="col" className="px-4 py-3">Ends</th>
            <th scope="col" className="px-4 py-3">Owner</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-100">
          {projects.map((project) => (
            <tr key={project.id} className="hover:bg-stone-50">
              <td className="px-4 py-3">
                <Link
                  to={`/projects/${project.id}`}
                  className="font-semibold text-stone-900 hover:text-forest-700 hover:underline"
                >
                  {project.name}
                </Link>
                <p className="text-xs text-stone-500">{TYPE_LABELS[project.type]}</p>
              </td>
              <td className="px-4 py-3 text-stone-600">
                {project.district && <span className="block">{project.district}</span>}
                <span className="text-xs text-stone-500">{project.state}</span>
              </td>
              <td className="px-4 py-3">
                <div className="flex flex-col items-start gap-1">
                  <StatusBadge status={project.status} />
                  {project.is_behind_schedule && <BehindScheduleBadge />}
                </div>
              </td>
              <td className="px-4 py-3">
                <ProjectProgressSummary project={project} />
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-stone-600">{formatDate(project.end_date)}</td>
              <td className="px-4 py-3 text-stone-600">{project.owner.name}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
