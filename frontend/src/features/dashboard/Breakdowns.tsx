/**
 * Projects by type and completion by state, as ranked horizontal bars in one colour.
 * (Ranked bars compare categories more exactly than a donut; the count is printed on every row.)
 */
import { formatNumber, formatPercent } from '../../lib/format'
import BarRow from './BarRow'
import { SERIES_COLOR } from './chartColors'
import type { StateBreakdown, TypeBreakdown } from './types'

const FULL = 100
const plural = (count: number, word: string) => `${formatNumber(count)} ${word}${count === 1 ? '' : 's'}`

export function ProjectsByType({ rows }: { rows: TypeBreakdown[] }) {
  if (rows.length === 0) return <p className="text-sm text-stone-500">No projects to show.</p>
  const largest = Math.max(...rows.map((row) => row.project_count))
  return (
    <ol className="space-y-3">
      {rows.map((row) => (
        <BarRow
          key={row.type}
          label={row.label}
          percent={(row.project_count / largest) * FULL}
          barClass={SERIES_COLOR}
          value={
            <>
              <span className="font-semibold text-stone-900">{plural(row.project_count, 'project')}</span>
              {row.average_completion_percent !== null && ` · ${formatPercent(row.average_completion_percent)} avg`}
            </>
          }
        />
      ))}
    </ol>
  )
}

export function CompletionByState({ rows }: { rows: StateBreakdown[] }) {
  if (rows.length === 0) return <p className="text-sm text-stone-500">No projects to show.</p>
  return (
    <ol className="space-y-3">
      {rows.map((row) => (
        <BarRow
          key={row.state}
          label={row.state}
          percent={row.average_completion_percent ?? 0}
          barClass={SERIES_COLOR}
          value={
            <>
              <span className="font-semibold text-stone-900">
                {/* null = every project here is cancelled or not started yet, so none counts toward completion */}
                {row.average_completion_percent === null ? 'Not counted' : formatPercent(row.average_completion_percent)}
              </span>
              {` · ${plural(row.project_count, 'project')}`}
              {row.trees_planted > 0 && ` · ${formatNumber(row.trees_planted)} trees`}
            </>
          }
        />
      ))}
    </ol>
  )
}
