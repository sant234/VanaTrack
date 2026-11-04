/**
 * Rules and helpers for the "Log progress" form.
 * They mirror the server (backend/app/services/progress_service.py and schemas/progress.py) so the user
 * gets instant feedback; the server still checks everything again.
 */
import { formatDate, formatNumber } from '../../lib/format'
import type { ProgressInput } from './types'

export const PROGRESS_MAX_VALUE = 2_000_000_000
export const UNREALISTIC_TARGET_MULTIPLIER = 10
export const CORRECTION_NOTE_MIN_LENGTH = 10
export const NOTE_MAX_LENGTH = 1000
const PERCENT = 100
const NOON = 12 // backdated entries are stored at midday, safely inside the chosen day in any timezone

export type ProgressFormValues = {
  value: string
  date: string // "YYYY-MM-DD"
  isCorrection: boolean
  note: string
}

export type ProgressFormField = 'value' | 'date' | 'is_correction' | 'note'
export type ProgressFormErrors = Partial<Record<ProgressFormField, string>>

/** What the form needs to know about the project to apply the rules. */
export type ProgressContext = {
  currentValue: number
  targetValue: number
  unit: string
  startDate: string // "YYYY-MM-DD"
  latestUpdateDate: string | null // "YYYY-MM-DD" in the user's timezone
  today: string // "YYYY-MM-DD"
}

const WHOLE_NUMBER = /^\d+$/

/** The typed total as a number, or null while it is empty or not a whole number. */
export function parseTotal(text: string): number | null {
  const trimmed = text.trim()
  return WHOLE_NUMBER.test(trimmed) ? Number(trimmed) : null
}

export function isDecrease(values: ProgressFormValues, context: ProgressContext): boolean {
  const total = parseTotal(values.value)
  return total !== null && total < context.currentValue
}

function valueProblem(text: string, context: ProgressContext): string | undefined {
  if (!text.trim()) return 'Enter the new total.'
  const total = parseTotal(text)
  if (total === null) return 'Enter a whole number, like 850 (no commas, decimals or minus sign).'
  if (total > PROGRESS_MAX_VALUE) return 'That number is too large.'
  if (total === context.currentValue) {
    return `This is the same as the current total (${formatNumber(context.currentValue)}).`
  }
  if (total > context.targetValue * UNREALISTIC_TARGET_MULTIPLIER) {
    return `That is more than ${UNREALISTIC_TARGET_MULTIPLIER}× the target. Please check for a typo.`
  }
  return undefined
}

function dateProblem(date: string, context: ProgressContext): string | undefined {
  // "YYYY-MM-DD" strings compare correctly as text.
  if (!date) return 'Choose the date of the count.'
  if (date > context.today) return 'The date cannot be in the future.'
  if (date < context.startDate) {
    return `The date cannot be before the project start date (${formatDate(context.startDate)}).`
  }
  if (context.latestUpdateDate && date < context.latestUpdateDate) {
    return `The date cannot be before the latest update (${formatDate(context.latestUpdateDate)}).`
  }
  return undefined
}

export function validateProgressForm(values: ProgressFormValues, context: ProgressContext): ProgressFormErrors {
  const errors: ProgressFormErrors = {
    value: valueProblem(values.value, context),
    date: dateProblem(values.date, context),
  }
  if (isDecrease(values, context) && !values.isCorrection) {
    errors.is_correction = 'The total is going down. Tick this box and explain why.'
  }
  if (values.isCorrection && values.note.trim().length < CORRECTION_NOTE_MIN_LENGTH) {
    errors.note = `Explain the correction in at least ${CORRECTION_NOTE_MIN_LENGTH} characters.`
  }
  if (values.note.trim().length > NOTE_MAX_LENGTH) {
    errors.note = `The note must be at most ${NOTE_MAX_LENGTH} characters.`
  }
  return Object.fromEntries(Object.entries(errors).filter(([, message]) => message)) as ProgressFormErrors
}

/** Convert validated form text into the API body. */
export function toProgressInput(values: ProgressFormValues, context: ProgressContext): ProgressInput {
  const input: ProgressInput = {
    value: Number(values.value.trim()),
    is_correction: values.isCorrection,
    note: values.note.trim() || null,
  }
  // Today means "now" (the server fills in the exact time). A past day is stored at noon that day.
  if (values.date !== context.today) {
    const [year, month, day] = values.date.split('-').map(Number)
    input.recorded_at = new Date(year, month - 1, day, NOON).toISOString()
  }
  return input
}

export type ProgressPreview = { from: number; to: number; change: number; percent: number }

/** Live preview for "600 → 850 (+250) · 85%", or null while the typed total is not a number. */
export function previewOf(values: ProgressFormValues, context: ProgressContext): ProgressPreview | null {
  const total = parseTotal(values.value)
  if (total === null) return null
  return {
    from: context.currentValue,
    to: total,
    change: total - context.currentValue,
    percent: Math.round((total * PERCENT * 10) / context.targetValue) / 10,
  }
}
