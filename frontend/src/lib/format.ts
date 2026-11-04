/** Display helpers. Indian number grouping (1,00,000) and short readable dates (4 Nov 2026). */

const INDIAN_LOCALE = 'en-IN'

const numberFormatter = new Intl.NumberFormat(INDIAN_LOCALE)
const rupeeFormatter = new Intl.NumberFormat(INDIAN_LOCALE, {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})
const dateFormatter = new Intl.DateTimeFormat(INDIAN_LOCALE, { day: 'numeric', month: 'short', year: 'numeric' })

export function formatNumber(value: number): string {
  return numberFormatter.format(value)
}

export function formatRupees(value: number): string {
  return rupeeFormatter.format(value)
}

/**
 * Format a "YYYY-MM-DD" date from the API.
 * Read as a local calendar date: new Date("2026-01-01") would be UTC midnight and can show the previous day.
 */
export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.slice(0, 10).split('-').map(Number)
  return dateFormatter.format(new Date(year, month - 1, day))
}

export function formatPercent(value: number): string {
  return `${Number.isInteger(value) ? value : value.toFixed(1)}%`
}
