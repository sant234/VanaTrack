import { apiRequest } from '../../lib/api'
import type { ProgressInput, ProgressUpdate } from './types'

const progressPath = (projectId: number) => `/projects/${projectId}/progress`

/** The full history, newest first. */
export function fetchProgressHistory(projectId: number): Promise<ProgressUpdate[]> {
  return apiRequest<ProgressUpdate[]>(progressPath(projectId))
}

export function logProgress(projectId: number, input: ProgressInput): Promise<ProgressUpdate> {
  return apiRequest<ProgressUpdate>(progressPath(projectId), { method: 'POST', body: JSON.stringify(input) })
}

/** Admins only, newest entry only. */
export function deleteProgressUpdate(projectId: number, updateId: number): Promise<void> {
  return apiRequest<void>(`${progressPath(projectId)}/${updateId}`, { method: 'DELETE' })
}
