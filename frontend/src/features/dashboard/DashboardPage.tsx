/**
 * The dashboard. Every number comes from the API (computed from the database on each request) and
 * refreshes when projects or progress change, or when the user returns to this tab.
 * The type filter lives in the URL (?type=solar) and applies to every widget.
 */
import { FolderPlus } from 'lucide-react'
import { lazy, Suspense, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import SelectField from '../../components/SelectField'
import Skeleton from '../../components/Skeleton'
import { EmptyState, ErrorState } from '../../components/StatePanels'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import RoleGate from '../auth/RoleGate'
import type { ProjectType } from '../projects/types'
import { useProjectOptions } from '../projects/useProjects'
import AttentionList from './AttentionList'
import { CompletionByState, ProjectsByType } from './Breakdowns'
import KpiCards from './KpiCards'
import ProgressByProject from './ProgressByProject'
import {
  useAttention,
  useCompletionTrend,
  useDashboardSummary,
  useProjectsByProgress,
  useStateBreakdown,
  useTypeBreakdown,
} from './useDashboard'

// The charting library is large: load it only when the trend chart is shown.
const CompletionTrendChart = lazy(() => import('./CompletionTrendChart'))

type QueryState<T> = { data: T | undefined; isError: boolean; error: Error | null; refetch: () => unknown }

/** A titled card that shows a skeleton while loading, a retry panel on error, else its content. */
function Panel<T>({
  title,
  subtitle,
  query,
  className = '',
  children,
}: {
  title: string
  subtitle?: string
  query: QueryState<T>
  className?: string
  children: (data: T) => ReactNode
}) {
  return (
    <section className={`rounded-2xl border border-stone-200 bg-white p-5 ${className}`} aria-label={title}>
      <h2 className="text-base font-semibold text-stone-900">{title}</h2>
      {subtitle && <p className="mt-0.5 text-xs text-stone-500">{subtitle}</p>}
      <div className="mt-4">
        {query.isError ? (
          <ErrorState message={query.error?.message ?? 'Unknown error'} onRetry={() => void query.refetch()} />
        ) : query.data === undefined ? (
          <Skeleton className="h-40" />
        ) : (
          children(query.data)
        )}
      </div>
    </section>
  )
}

function TypeFilter({ value, onChange }: { value: string; onChange: (type: string) => void }) {
  const options = useProjectOptions()
  return (
    <SelectField
      label="Project type"
      hideLabel
      placeholder="All project types"
      options={options.data?.types ?? []}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="w-full sm:w-56"
    />
  )
}

export default function DashboardPage() {
  useDocumentTitle('Dashboard')
  const [searchParams, setSearchParams] = useSearchParams()
  const typeFilter = searchParams.get('type') ?? ''
  const type = (typeFilter || undefined) as ProjectType | undefined

  const summary = useDashboardSummary(type)
  const byProgress = useProjectsByProgress(type)
  const byType = useTypeBreakdown(type)
  const byState = useStateBreakdown(type)
  const trend = useCompletionTrend(type)
  const attention = useAttention(type)

  function changeType(nextType: string) {
    const next = new URLSearchParams(window.location.search)
    if (nextType) next.set('type', nextType)
    else next.delete('type')
    setSearchParams(next, { replace: true })
  }

  const isFreshDatabase = summary.data?.total_projects === 0 && !typeFilter

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-stone-900">Dashboard</h1>
          <p className="text-sm text-stone-500">Live figures from every project and progress update.</p>
        </div>
        <TypeFilter value={typeFilter} onChange={changeType} />
      </div>

      {isFreshDatabase ? (
        <EmptyState
          icon={FolderPlus}
          title="No projects yet"
          description="Once projects are created and progress is logged, their figures appear here."
          action={
            <RoleGate roles={['admin', 'manager']}>
              <Link to="/projects/new" className="inline-flex min-h-10 items-center text-sm font-semibold text-forest-700 hover:underline">
                Create the first project
              </Link>
            </RoleGate>
          }
        />
      ) : (
        <>
          {summary.isError ? (
            <ErrorState message={summary.error.message} onRetry={() => void summary.refetch()} />
          ) : summary.data ? (
            <KpiCards summary={summary.data} />
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6" role="status" aria-label="Loading key figures">
              {Array.from({ length: 6 }, (_, index) => (
                <Skeleton key={index} className="h-28" />
              ))}
            </div>
          )}

          <div className="grid gap-5 lg:grid-cols-2">
            <Panel title="Progress by project" subtitle="Top 10 by completion" query={byProgress}>
              {(projects) => <ProgressByProject projects={projects} />}
            </Panel>
            <Panel
              title="Average completion over time"
              subtitle="Started, non-cancelled projects · each counts up to 100%"
              query={trend}
            >
              {(points) => (
                <Suspense fallback={<Skeleton className="h-60" />}>
                  <CompletionTrendChart points={points} />
                </Suspense>
              )}
            </Panel>
            <Panel title="Projects by type" subtitle="Cancelled and not-yet-started projects do not count toward completion" query={byType}>
              {(rows) => <ProjectsByType rows={rows} />}
            </Panel>
            <Panel
              title="Completion by state"
              subtitle="Average completion · projects · trees. Cancelled and not-yet-started projects are not counted."
              query={byState}
            >
              {(rows) => <CompletionByState rows={rows} />}
            </Panel>
          </div>

          <Panel title="Needs attention" subtitle="Behind schedule, or active with no update in 30+ days" query={attention}>
            {(items) => <AttentionList items={items} />}
          </Panel>
        </>
      )}
    </section>
  )
}
