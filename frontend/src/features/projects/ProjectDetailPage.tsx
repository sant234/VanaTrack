import { ArrowLeft, CalendarRange, IndianRupee, MapPin, Pencil, Trash2, UserRound } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import Alert from '../../components/Alert'
import Button from '../../components/Button'
import ConfirmDialog from '../../components/ConfirmDialog'
import ProgressBar from '../../components/ProgressBar'
import Skeleton from '../../components/Skeleton'
import { ErrorState } from '../../components/StatePanels'
import { ApiError } from '../../lib/api'
import { formatDate, formatNumber, formatPercent, formatRupees, formatTimestampDate } from '../../lib/format'
import ProjectActivityPanel from '../activity/ProjectActivityPanel'
import ProjectProgressSection from '../progress/ProjectProgressSection'
import { BehindScheduleBadge, StatusBadge } from './ProjectBadges'
import ProjectNotFound from './ProjectNotFound'
import { TYPE_LABELS } from './projectLabels'
import type { Project } from './types'
import { useDeleteProject, useProject } from './useProjects'
import { useProjectIdParam } from './useProjectIdParam'

const NOT_FOUND_STATUS = 404

function DetailItem({ icon: Icon, label, children }: { icon: typeof MapPin; label: string; children: ReactNode }) {
  return (
    <div className="flex gap-3">
      <Icon aria-hidden className="mt-0.5 size-5 shrink-0 text-stone-400" />
      <div>
        <dt className="text-xs font-medium tracking-wide text-stone-500 uppercase">{label}</dt>
        <dd className="mt-0.5 text-sm text-stone-900">{children}</dd>
      </div>
    </div>
  )
}

function ProgressCard({ project }: { project: Project }) {
  return (
    <div className="rounded-2xl border border-stone-200 bg-white p-5">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-sm text-stone-500">Progress</p>
          <p className="text-3xl font-bold text-stone-900">{formatPercent(project.progress_percent)}</p>
        </div>
        <p className="text-sm text-stone-600">
          <span className="font-semibold text-stone-900">{formatNumber(project.current_value)}</span> of{' '}
          {formatNumber(project.target_value)} {project.unit}
        </p>
      </div>
      <div className="mt-3">
        <ProgressBar percent={project.progress_percent} label="Project progress" />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-stone-600">
        <span>{formatPercent(project.expected_percent)} of the timeline has passed.</span>
        {project.is_behind_schedule && <BehindScheduleBadge />}
        {project.is_target_exceeded && (
          <span className="rounded-full bg-forest-100 px-2 py-0.5 text-xs font-semibold text-forest-900">
            Exceeded target
          </span>
        )}
      </div>
      <p className="mt-3 text-xs text-stone-500">
        {project.last_updated_at ? `Last progress update ${formatTimestampDate(project.last_updated_at)}.` : 'No progress logged yet.'}
      </p>
    </div>
  )
}

function ProjectDetails({ project }: { project: Project }) {
  const navigate = useNavigate()
  const [isConfirmOpen, setIsConfirmOpen] = useState(false)
  const deleteProject = useDeleteProject(project.id)

  async function confirmDelete() {
    try {
      await deleteProject.mutateAsync()
      navigate('/projects', { replace: true, state: { notice: `Project “${project.name}” was deleted.` } })
    } catch {
      setIsConfirmOpen(false) // the error message is shown on the page
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold break-words text-stone-900">{project.name}</h1>
            <StatusBadge status={project.status} />
          </div>
          <p className="mt-1 text-sm text-stone-500">{TYPE_LABELS[project.type]}</p>
        </div>
        {project.can_edit && (
          <div className="flex gap-2">
            <Link
              to={`/projects/${project.id}/edit`}
              className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm font-semibold text-stone-800 hover:bg-stone-100"
            >
              <Pencil aria-hidden className="size-4" />
              Edit
            </Link>
            <Button variant="secondary" onClick={() => setIsConfirmOpen(true)} className="text-red-700">
              <Trash2 aria-hidden className="size-4" />
              Delete
            </Button>
          </div>
        )}
      </div>

      {deleteProject.isError && (
        <Alert>
          {deleteProject.error instanceof ApiError ? deleteProject.error.message : 'Could not delete the project.'}
        </Alert>
      )}

      <ProgressCard project={project} />

      <ProjectProgressSection project={project} />

      <dl className="grid gap-5 rounded-2xl border border-stone-200 bg-white p-5 sm:grid-cols-2">
        <DetailItem icon={MapPin} label="Location">
          {project.district ? `${project.district}, ` : ''}
          {project.state}
        </DetailItem>
        <DetailItem icon={CalendarRange} label="Timeline">
          {formatDate(project.start_date)} – {formatDate(project.end_date)}
        </DetailItem>
        <DetailItem icon={IndianRupee} label="Budget">
          {project.budget_inr === null ? 'Not set' : formatRupees(project.budget_inr)}
        </DetailItem>
        <DetailItem icon={UserRound} label="Owner">
          {project.owner.name}
        </DetailItem>
      </dl>

      {project.description && (
        <div className="rounded-2xl border border-stone-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-stone-900">Description</h2>
          <p className="mt-2 text-sm whitespace-pre-line text-stone-700">{project.description}</p>
        </div>
      )}

      <ProjectActivityPanel projectId={project.id} isProjectGone={deleteProject.isPending || deleteProject.isSuccess} />

      <p className="text-xs text-stone-500">
        Created {formatTimestampDate(project.created_at)} · Last edited {formatTimestampDate(project.updated_at)}
      </p>

      <ConfirmDialog
        open={isConfirmOpen}
        title="Delete this project?"
        confirmLabel="Delete project"
        isConfirming={deleteProject.isPending}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setIsConfirmOpen(false)}
      >
        <p>
          “{project.name}” will be removed permanently. This cannot be undone.
        </p>
      </ConfirmDialog>
    </div>
  )
}

export default function ProjectDetailPage() {
  const projectId = useProjectIdParam()
  const project = useProject(projectId)

  function renderBody() {
    const isMissing =
      Number.isNaN(projectId) || (project.error instanceof ApiError && project.error.status === NOT_FOUND_STATUS)
    if (isMissing) return <ProjectNotFound />
    if (project.isError) return <ErrorState message={project.error.message} onRetry={() => void project.refetch()} />
    if (!project.data) {
      return (
        <div className="space-y-4" role="status" aria-label="Loading project">
          <Skeleton className="h-10 w-2/3" />
          <Skeleton className="h-36" />
          <Skeleton className="h-32" />
        </div>
      )
    }
    return <ProjectDetails project={project.data} />
  }

  return (
    <section className="mx-auto max-w-4xl space-y-4">
      <Link to="/projects" className="inline-flex items-center gap-1 text-sm font-medium text-stone-600 hover:text-forest-700">
        <ArrowLeft aria-hidden className="size-4" />
        All projects
      </Link>
      {renderBody()}
    </section>
  )
}
