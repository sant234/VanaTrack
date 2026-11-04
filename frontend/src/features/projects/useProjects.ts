/**
 * Data hooks for projects, built on TanStack Query.
 *
 * Every change (create, update, delete) marks the cached project data as out of date ("invalidate"),
 * so lists, detail pages and later the dashboard refetch and show the new values automatically.
 */
import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'

import {
  createProject,
  deleteProject,
  fetchProject,
  fetchProjectOptions,
  fetchProjects,
  updateProject,
} from './projectsApi'
import type { ProjectInput, ProjectListParams } from './types'

const OPTIONS_CACHE_MS = 60 * 60 * 1000 // dropdown choices rarely change

export const projectKeys = {
  lists: ['projects'] as const,
  list: (params: ProjectListParams) => ['projects', params] as const,
  detail: (projectId: number) => ['project', projectId] as const,
  options: ['project-options'] as const,
}

/**
 * Everything that shows project numbers must refresh after a change: lists, the dashboard (Prompt 4),
 * the activity log (Prompt 5), and the changed project's own page and progress history.
 */
export function invalidateProjectData(queryClient: QueryClient, projectId?: number) {
  void queryClient.invalidateQueries({ queryKey: projectKeys.lists })
  void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  void queryClient.invalidateQueries({ queryKey: ['activity'] })
  if (projectId !== undefined) {
    void queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    void queryClient.invalidateQueries({ queryKey: ['progress', projectId] })
  }
}

export function useProjectList(params: ProjectListParams) {
  return useQuery({
    queryKey: projectKeys.list(params),
    queryFn: () => fetchProjects(params),
    placeholderData: (previous) => previous, // keep showing old results while new filters load
  })
}

export function useProject(projectId: number) {
  return useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => fetchProject(projectId),
    enabled: Number.isInteger(projectId) && projectId > 0,
  })
}

export function useProjectOptions() {
  return useQuery({ queryKey: projectKeys.options, queryFn: fetchProjectOptions, staleTime: OPTIONS_CACHE_MS })
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: ProjectInput) => createProject(input),
    onSuccess: (project) => invalidateProjectData(queryClient, project.id),
  })
}

export function useUpdateProject(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: ProjectInput) => updateProject(projectId, input),
    onSuccess: (project) => {
      queryClient.setQueryData(projectKeys.detail(projectId), project)
      invalidateProjectData(queryClient, projectId)
    },
  })
}

export function useDeleteProject(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => deleteProject(projectId),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: projectKeys.detail(projectId) })
      invalidateProjectData(queryClient)
    },
  })
}
