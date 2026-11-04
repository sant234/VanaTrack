export type ProgressUpdate = {
  id: number
  /** The running total after this update, e.g. 850. */
  value: number
  /** The running total just before it, e.g. 600. Filled in by the server. */
  previous_value: number
  /** value − previous_value, e.g. +250 or −150. */
  change: number
  is_correction: boolean
  note: string | null
  recorded_at: string
  created_at: string
  author: { id: number; name: string }
  can_delete: boolean
}

export type ProgressInput = {
  value: number
  /** Leave out to mean "now". Must include a timezone. */
  recorded_at?: string
  is_correction: boolean
  note: string | null
}
