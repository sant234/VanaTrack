import { apiRequest } from '../../lib/api'
import type { Project, ProjectInput, ProjectListParams, ProjectOptions } from './types'

function toQueryString(params: ProjectListParams): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === '' || value === false) continue
    query.set(key, String(value))
  }
  const text = query.toString()
  return text ? `?${text}` : ''
}

export function fetchProjects(params: ProjectListParams): Promise<Project[]> {
  return apiRequest<Project[]>(`/projects${toQueryString(params)}`)
}

export function fetchProject(projectId: number): Promise<Project> {
  return apiRequest<Project>(`/projects/${projectId}`)
}

export function fetchProjectOptions(): Promise<ProjectOptions> {
  return apiRequest<ProjectOptions>('/projects/options')
}

export function createProject(input: ProjectInput): Promise<Project> {
  return apiRequest<Project>('/projects', { method: 'POST', body: JSON.stringify(input) })
}

export function updateProject(projectId: number, input: ProjectInput): Promise<Project> {
  return apiRequest<Project>(`/projects/${projectId}`, { method: 'PATCH', body: JSON.stringify(input) })
}

export function deleteProject(projectId: number): Promise<void> {
  return apiRequest<void>(`/projects/${projectId}`, { method: 'DELETE' })
}
