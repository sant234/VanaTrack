import { FolderPlus, Plus, SearchX } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'

import Alert from '../../components/Alert'
import Button from '../../components/Button'
import Skeleton from '../../components/Skeleton'
import { EmptyState, ErrorState } from '../../components/StatePanels'
import { useDebouncedValue } from '../../lib/useDebouncedValue'
import RoleGate from '../auth/RoleGate'
import { useAuth } from '../auth/useAuth'
import ProjectCard from './ProjectCard'
import ProjectFilters from './ProjectFilters'
import ProjectsTable from './ProjectsTable'
import { useProjectFilters } from './useProjectFilters'
import { useProjectList, useProjectOptions } from './useProjects'

const SEARCH_DELAY_MS = 300
const SKELETON_ROWS = 3
const CREATOR_ROLES = ['admin', 'manager'] as const

function NewProjectButton() {
  return (
    <RoleGate roles={[...CREATOR_ROLES]}>
      <Link
        to="/projects/new"
        className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-forest-700 px-4 py-2 text-sm font-semibold text-white hover:bg-forest-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forest-500"
      >
        <Plus aria-hidden className="size-4" />
        New project
      </Link>
    </RoleGate>
  )
}

function LoadingList() {
  return (
    <div className="space-y-3" role="status" aria-label="Loading projects">
      {Array.from({ length: SKELETON_ROWS }, (_, index) => (
        <Skeleton key={index} className="h-28" />
      ))}
    </div>
  )
}

export default function ProjectsListPage() {
  const { user } = useAuth()
  const location = useLocation()
  const notice = (location.state as { notice?: string } | null)?.notice

  const controls = useProjectFilters()
  const debouncedSearch = useDebouncedValue(controls.filters.search.trim(), SEARCH_DELAY_MS)
  const { data: projects, isPending, isError, error, refetch } = useProjectList({
    ...controls.apiParams,
    search: debouncedSearch || undefined,
  })
  const { data: options } = useProjectOptions()

  function renderResults() {
    if (isPending) return <LoadingList />
    if (isError) return <ErrorState message={error.message} onRetry={() => void refetch()} />
    if (projects.length === 0 && controls.hasActiveFilters) {
      return (
        <EmptyState
          icon={SearchX}
          title="No projects match your filters"
          description="Try a different search or remove some filters."
          action={
            <Button variant="secondary" onClick={controls.clearFilters}>
              Clear filters
            </Button>
          }
        />
      )
    }
    if (projects.length === 0) {
      return (
        <EmptyState
          icon={FolderPlus}
          title="No projects yet"
          description="Projects you and your team create will appear here."
          action={<NewProjectButton />}
        />
      )
    }
    return (
      <>
        <ul className="space-y-3 lg:hidden">
          {projects.map((project) => (
            <li key={project.id}>
              <ProjectCard project={project} />
            </li>
          ))}
        </ul>
        <div className="hidden lg:block">
          <ProjectsTable projects={projects} />
        </div>
      </>
    )
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-stone-900">Projects</h1>
          {projects && (
            <p className="text-sm text-stone-500" aria-live="polite">
              {projects.length} {projects.length === 1 ? 'project' : 'projects'}
            </p>
          )}
        </div>
        <NewProjectButton />
      </div>

      {notice && <Alert tone="info">{notice}</Alert>}

      {user && <ProjectFilters controls={controls} options={options} role={user.role} />}

      {renderResults()}
    </section>
  )
}
