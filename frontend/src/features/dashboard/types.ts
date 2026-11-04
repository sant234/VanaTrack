import type { ProjectStatus, ProjectType } from '../projects/types'

export type DashboardSummary = {
  total_projects: number
  active_projects: number
  /** Average of each counted project's completion % (capped at 100). Counted = started, not cancelled. */
  average_completion_percent: number
  completion_project_count: number
  trees_planted: number
  estimated_co2_tonnes_per_year: number
  co2_kg_per_tree_per_year: number
  behind_schedule_count: number
  exceeded_target_count: number
  needs_attention_count: number
}

export type TypeBreakdown = {
  type: ProjectType
  label: string
  project_count: number
  average_completion_percent: number | null
}

export type StateBreakdown = {
  state: string
  project_count: number
  average_completion_percent: number | null
  trees_planted: number
}

export type TrendPoint = {
  month: string // "2026-11"
  average_completion_percent: number | null
  project_count: number
}

export type AttentionReason = 'behind_schedule' | 'no_recent_update'

export type AttentionItem = {
  id: number
  name: string
  type: ProjectType
  status: ProjectStatus
  owner_name: string
  progress_percent: number
  expected_percent: number
  last_updated_at: string | null
  days_since_update: number | null
  reasons: AttentionReason[]
}
