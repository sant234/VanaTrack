/** One entry of the activity log, as returned by GET /api/activity. */
export type ActivityAction =
  | 'created'
  | 'updated'
  | 'deleted'
  | 'progress_logged'
  | 'progress_deleted'
  | 'role_changed'
  | 'user_deactivated'
  | 'user_activated'

export type ActivityEntry = {
  id: number
  action: ActivityAction
  entity_type: 'project' | 'progress_update' | 'user'
  entity_id: number
  /** null once the project has been deleted. */
  project_id: number | null
  /** Still filled in for a deleted project when the server saved its name in details. */
  project_name: string | null
  user_id: number
  user_name: string
  created_at: string
  /** Action-specific data, e.g. {"from": 600, "to": 850, "is_correction": false}. */
  details: Record<string, unknown>
  /** A full sentence written by the server, e.g. "Field Manager logged progress on Western Ghats: 600 → 850". */
  summary: string
}

export type ActivityParams = {
  limit: number
  projectId?: number
}
