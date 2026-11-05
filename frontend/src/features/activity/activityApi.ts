import { apiRequest } from '../../lib/api'
import type { ActivityEntry, ActivityParams } from './types'

/** Newest first. With projectId, only that project's entries. */
export function fetchActivity({ limit, projectId }: ActivityParams): Promise<ActivityEntry[]> {
  const query = new URLSearchParams({ limit: String(limit) })
  if (projectId !== undefined) query.set('project_id', String(projectId))
  return apiRequest<ActivityEntry[]>(`/activity?${query.toString()}`)
}
