import type { ProjectStatus, ProjectType } from './types'

export const STATUS_LABELS: Record<ProjectStatus, string> = {
  planned: 'Planned',
  active: 'Active',
  on_hold: 'On hold',
  completed: 'Completed',
  cancelled: 'Cancelled',
}

export const TYPE_LABELS: Record<ProjectType, string> = {
  afforestation: 'Afforestation',
  water_conservation: 'Water conservation',
  solar: 'Solar',
  waste_management: 'Waste management',
  other: 'Other',
}

/** Suggested unit for each type, pre-filled in the form so totals use one consistent unit. */
export const SUGGESTED_UNITS: Record<ProjectType, string> = {
  afforestation: 'trees',
  water_conservation: 'kL water',
  solar: 'kW',
  waste_management: 'kg waste',
  other: '',
}
