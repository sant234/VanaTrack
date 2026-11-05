/** /activity: the organisation-wide log of changes, newest first. Every logged-in user may read it. */
import { History } from 'lucide-react'

import Skeleton from '../../components/Skeleton'
import { EmptyState, ErrorState } from '../../components/StatePanels'
import ActivityFeed from './ActivityFeed'
import { useActivity } from './useActivity'

const FEED_LIMIT = 50

export default function ActivityPage() {
  const activity = useActivity({ limit: FEED_LIMIT })

  function renderBody() {
    if (activity.isPending) {
      return (
        <div className="space-y-3" role="status" aria-label="Loading activity">
          <Skeleton className="h-14" />
          <Skeleton className="h-14" />
          <Skeleton className="h-14" />
        </div>
      )
    }
    if (activity.isError) {
      return <ErrorState message={activity.error.message} onRetry={() => void activity.refetch()} />
    }
    if (activity.data.length === 0) {
      return (
        <EmptyState
          icon={History}
          title="No activity yet"
          description="Creating or editing projects and logging progress will show up here."
        />
      )
    }
    return (
      <div className="rounded-2xl border border-stone-200 bg-white p-4 sm:p-5">
        <ActivityFeed entries={activity.data} showProject />
      </div>
    )
  }

  return (
    <section className="mx-auto max-w-3xl space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-stone-900">Activity</h1>
        <p className="mt-1 text-sm text-stone-500">
          The latest {FEED_LIMIT} changes across all projects, newest first.
        </p>
      </div>
      {renderBody()}
    </section>
  )
}
