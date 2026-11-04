/** The progress area of a project page: "Log progress" button, chart and history timeline. */
import { Plus } from 'lucide-react'
import { lazy, Suspense, useState } from 'react'

import Alert from '../../components/Alert'
import Button from '../../components/Button'
import Skeleton from '../../components/Skeleton'
import { ErrorState } from '../../components/StatePanels'
import { toDateInput, todayAsDateInput } from '../../lib/format'
import type { Project } from '../projects/types'
import LogProgressDialog from './LogProgressDialog'
import ProgressTimeline from './ProgressTimeline'
import type { ProgressContext } from './progressForm'
import type { ProgressUpdate } from './types'
import { useProgressHistory } from './useProgress'

const CLOSED_STATUSES: Project['status'][] = ['completed', 'cancelled']

// The charting library is large; load it only when a chart is actually shown, not on every page.
const ProgressChart = lazy(() => import('./ProgressChart'))

function contextFor(project: Project, history: ProgressUpdate[]): ProgressContext {
  const latest = history[0]
  return {
    currentValue: project.current_value,
    targetValue: project.target_value,
    unit: project.unit,
    startDate: project.start_date,
    latestUpdateDate: latest ? toDateInput(new Date(latest.recorded_at)) : null,
    today: todayAsDateInput(),
  }
}

export default function ProjectProgressSection({ project }: { project: Project }) {
  const history = useProgressHistory(project.id)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [savedMessage, setSavedMessage] = useState<string | null>(null)

  const isClosed = CLOSED_STATUSES.includes(project.status)
  const canLog = project.can_edit && !isClosed

  function renderBody() {
    if (history.isPending) {
      return (
        <div className="space-y-3" role="status" aria-label="Loading progress history">
          <Skeleton className="h-56" />
          <Skeleton className="h-20" />
        </div>
      )
    }
    if (history.isError) {
      return <ErrorState message={history.error.message} onRetry={() => void history.refetch()} />
    }
    return (
      <div className="grid gap-5 lg:grid-cols-5">
        {history.data.length > 0 && (
          <div className="rounded-2xl border border-stone-200 bg-white p-5 lg:col-span-3">
            <h3 className="mb-3 text-sm font-semibold text-stone-900">{`Total ${project.unit} over time`}</h3>
            <Suspense fallback={<Skeleton className="h-[260px]" />}>
              <ProgressChart
                history={history.data}
                startDate={project.start_date}
                targetValue={project.target_value}
                unit={project.unit}
              />
            </Suspense>
          </div>
        )}
        <div
          className={`rounded-2xl border border-stone-200 bg-white p-5 ${history.data.length > 0 ? 'lg:col-span-2' : 'lg:col-span-5'}`}
        >
          <h3 className="mb-4 text-sm font-semibold text-stone-900">History</h3>
          <ProgressTimeline projectId={project.id} history={history.data} unit={project.unit} />
        </div>
      </div>
    )
  }

  return (
    <section aria-labelledby="progress-heading" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="progress-heading" className="text-lg font-bold text-stone-900">
          Progress updates
        </h2>
        {canLog && (
          <Button
            onClick={() => {
              setSavedMessage(null)
              setIsDialogOpen(true)
            }}
            disabled={!history.data}
          >
            <Plus aria-hidden className="size-4" />
            Log progress
          </Button>
        )}
      </div>

      {project.can_edit && isClosed && (
        <Alert tone="info">This project is {project.status}, so new progress cannot be logged.</Alert>
      )}
      {savedMessage && <Alert tone="info">{savedMessage}</Alert>}

      {renderBody()}

      {/* Mounted only while open, so every opening starts with a fresh, empty form. */}
      {isDialogOpen && history.data && (
        <LogProgressDialog
          open
          projectId={project.id}
          context={contextFor(project, history.data)}
          onClose={() => setIsDialogOpen(false)}
          onSaved={(message) => {
            setIsDialogOpen(false)
            setSavedMessage(message)
          }}
        />
      )}
    </section>
  )
}
