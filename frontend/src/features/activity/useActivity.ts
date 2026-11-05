/**
 * Data hook for the activity log. Every key starts with "activity", so invalidateProjectData (run after
 * every project and progress change) refreshes the feed and each project's "Recent activity" at once.
 */
import { useQuery } from '@tanstack/react-query'

import { fetchActivity } from './activityApi'
import type { ActivityParams } from './types'

export const activityKeys = {
  all: ['activity'] as const,
  list: (params: ActivityParams) => ['activity', params] as const,
}

export function useActivity(params: ActivityParams) {
  return useQuery({
    queryKey: activityKeys.list(params),
    queryFn: () => fetchActivity(params),
    // Other people's changes are what this page is for, so check again whenever the tab regains focus.
    refetchOnWindowFocus: 'always',
  })
}
