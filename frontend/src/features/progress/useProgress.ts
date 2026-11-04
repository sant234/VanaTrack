/**
 * Data hooks for a project's progress history.
 *
 * After logging or deleting an update, every screen that shows this project's numbers is marked
 * out of date, so the detail page, project list and dashboard all show the new total without a reload.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { invalidateProjectData } from '../projects/useProjects'
import { deleteProgressUpdate, fetchProgressHistory, logProgress } from './progressApi'
import type { ProgressInput } from './types'

export const progressKeys = {
  history: (projectId: number) => ['progress', projectId] as const,
}

export function useProgressHistory(projectId: number) {
  return useQuery({
    queryKey: progressKeys.history(projectId),
    queryFn: () => fetchProgressHistory(projectId),
  })
}

export function useLogProgress(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: ProgressInput) => logProgress(projectId, input),
    onSuccess: () => invalidateProjectData(queryClient, projectId),
  })
}

export function useDeleteProgressUpdate(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (updateId: number) => deleteProgressUpdate(projectId, updateId),
    onSuccess: () => invalidateProjectData(queryClient, projectId),
  })
}
