export type ProjectType = 'afforestation' | 'water_conservation' | 'solar' | 'waste_management' | 'other'

export type ProjectStatus = 'planned' | 'active' | 'on_hold' | 'completed' | 'cancelled'

export type Project = {
  id: number
  name: string
  description: string | null
  type: ProjectType
  status: ProjectStatus
  target_value: number
  unit: string
  state: string
  district: string | null
  start_date: string
  end_date: string
  budget_inr: number | null
  owner: { id: number; name: string }
  created_at: string
  updated_at: string
  // Calculated by the server on every request (never stored).
  current_value: number
  progress_percent: number
  expected_percent: number
  is_behind_schedule: boolean
  last_updated_at: string | null
  can_edit: boolean
}

/** Body for create (all fields) and update (same shape; the server applies the fields sent). */
export type ProjectInput = {
  name: string
  description: string | null
  type: ProjectType
  status: ProjectStatus
  target_value: number
  unit: string
  state: string
  district: string | null
  start_date: string
  end_date: string
  budget_inr: number | null
}

export type Option = { value: string; label: string }

export type ProjectOptions = { types: Option[]; statuses: Option[]; states: string[] }

export type ProjectSort = 'name' | 'created_at' | 'end_date' | 'progress'
export type SortOrder = 'asc' | 'desc'

export type ProjectListParams = {
  search?: string
  type?: string
  status?: string
  state?: string
  mine?: boolean
  sort?: ProjectSort
  order?: SortOrder
}
