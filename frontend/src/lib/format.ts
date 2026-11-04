/** Display helpers. Indian number grouping (1,00,000) and short readable dates (4 Nov 2026). */

const INDIAN_LOCALE = 'en-IN'

const numberFormatter = new Intl.NumberFormat(INDIAN_LOCALE)
const rupeeFormatter = new Intl.NumberFormat(INDIAN_LOCALE, {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})
const dateFormatter = new Intl.DateTimeFormat(INDIAN_LOCALE, { day: 'numeric', month: 'short', year: 'numeric' })
const dateTimeFormatter = new Intl.DateTimeFormat(INDIAN_LOCALE, {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})

export function formatNumber(value: number): string {
  return numberFormatter.format(value)
}

export function formatRupees(value: number): string {
  return rupeeFormatter.format(value)
}

/**
 * Format a calendar date from the API ("YYYY-MM-DD", e.g. a project's start_date).
 * Read as a local calendar date: new Date("2026-01-01") would be UTC midnight and can show the previous day.
 * For moments in time (created_at, recorded_at) use formatTimestampDate instead.
 */
export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.slice(0, 10).split('-').map(Number)
  return dateFormatter.format(new Date(year, month - 1, day))
}

export function formatPercent(value: number): string {
  return `${Number.isInteger(value) ? value : value.toFixed(1)}%`
}

/** A moment in time (e.g. "2026-11-03T20:45:00Z") as the calendar day it was in the user's own timezone. */
export function formatTimestampDate(isoTimestamp: string): string {
  return dateFormatter.format(new Date(isoTimestamp))
}

/** A moment in time with the clock time, e.g. "4 Nov 2026, 3:42 pm". */
export function formatTimestamp(isoTimestamp: string): string {
  return dateTimeFormatter.format(new Date(isoTimestamp))
}

/** A change with its sign, e.g. +250 or −150 (a true minus sign, easier to read than a hyphen). */
export function formatSignedNumber(value: number): string {
  if (value > 0) return `+${formatNumber(value)}`
  if (value < 0) return `−${formatNumber(Math.abs(value))}`
  return '0'
}

/** Today's date in the user's timezone as "YYYY-MM-DD" (the format of <input type="date">). */
export function todayAsDateInput(): string {
  return toDateInput(new Date())
}

/** A moment in time as the user's local "YYYY-MM-DD". */
export function toDateInput(moment: Date): string {
  const pad = (part: number) => String(part).padStart(2, '0')
  return `${moment.getFullYear()}-${pad(moment.getMonth() + 1)}-${pad(moment.getDate())}`
}
