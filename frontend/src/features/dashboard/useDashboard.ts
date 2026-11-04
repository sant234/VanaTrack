/**
 * Data for the dashboard. Every query key starts with "dashboard", so any project or progress change
 * (see invalidateProjectData) marks all of it out of date at once.
 *
 * refetchOnWindowFocus: 'always' — the app normally treats data as fresh for a minute. For the dashboard
 * that is too long: after logging progress in another tab, switching back must show the new numbers.
 */
import { useQuery } from '@tanstack/react-query'

import { apiRequest } from '../../lib/api'
import { fetchProjects } from '../projects/projectsApi'
import type { ProjectType } from '../projects/types'
import type { AttentionItem, DashboardSummary, StateBreakdown, TrendPoint, TypeBreakdown } from './types'

const ALWAYS_REFRESH = { refetchOnWindowFocus: 'always' as const }

function typeQuery(type: ProjectType | undefined): string {
  return type ? `?type=${type}` : ''
}

function useDashboardEndpoint<T>(endpoint: string, type: ProjectType | undefined) {
  return useQuery({
    queryKey: ['dashboard', endpoint, type ?? 'all'],
    queryFn: () => apiRequest<T>(`/dashboard/${endpoint}${typeQuery(type)}`),
    ...ALWAYS_REFRESH,
  })
}

export const useDashboardSummary = (type?: ProjectType) => useDashboardEndpoint<DashboardSummary>('summary', type)
export const useTypeBreakdown = (type?: ProjectType) => useDashboardEndpoint<TypeBreakdown[]>('by-type', type)
export const useStateBreakdown = (type?: ProjectType) => useDashboardEndpoint<StateBreakdown[]>('by-state', type)
export const useCompletionTrend = (type?: ProjectType) => useDashboardEndpoint<TrendPoint[]>('trend', type)
export const useAttention = (type?: ProjectType) => useDashboardEndpoint<AttentionItem[]>('attention', type)

/** Projects with the most progress first, from the same endpoint as the project list. */
export function useProjectsByProgress(type?: ProjectType) {
  const params = { type, sort: 'progress' as const, order: 'desc' as const }
  return useQuery({
    queryKey: ['projects', params], // under "projects", so project changes refresh it too
    queryFn: () => fetchProjects(params),
    ...ALWAYS_REFRESH,
  })
}
