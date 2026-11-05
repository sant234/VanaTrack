/** "Recent activity" on a project page: the latest changes to this one project. */
import { History } from 'lucide-react'
import { Link } from 'react-router-dom'

import Skeleton from '../../components/Skeleton'
import { EmptyState, ErrorState } from '../../components/StatePanels'
import ActivityFeed from './ActivityFeed'
import { useActivity } from './useActivity'

const RECENT_LIMIT = 10

/**
 * `isProjectGone`: true once the project is being deleted. Its activity can then no longer be fetched
 * (the API answers 404), so the panel stops asking and keeps showing what it has until the page changes.
 */
export default function ProjectActivityPanel({ projectId, isProjectGone }: { projectId: number; isProjectGone: boolean }) {
  const activity = useActivity({ limit: RECENT_LIMIT, projectId }, { enabled: !isProjectGone })

  function renderBody() {
    if (activity.isPending) {
      return (
        <div className="space-y-3" role="status" aria-label="Loading recent activity">
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
        </div>
      )
    }
    if (activity.isError) {
      return <ErrorState message={activity.error.message} onRetry={() => void activity.refetch()} />
    }
    if (activity.data.length === 0) {
      return <EmptyState icon={History} title="No activity yet" description="Changes to this project will appear here." />
    }
    return <ActivityFeed entries={activity.data} showProject={false} />
  }

  return (
    <section aria-labelledby="recent-activity-heading" className="rounded-2xl border border-stone-200 bg-white p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 id="recent-activity-heading" className="text-lg font-bold text-stone-900">
          Recent activity
        </h2>
        <Link to="/activity" className="text-sm font-medium text-forest-700 hover:text-forest-900 hover:underline">
          All activity
        </Link>
      </div>
      {renderBody()}
    </section>
  )
}
