/**
 * Average completion at the end of each of the last 12 months (the latest point is "today").
 * One series, so no legend box; months before any project started are gaps, not zeros.
 * A table of the same numbers is available under the chart for screen readers and exact reading.
 */
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { formatPercent } from '../../lib/format'
import { SERIES_HEX } from './chartColors'
import type { TrendPoint } from './types'

const GRID_COLOR = '#e7e5e4'
const AXIS_TEXT_COLOR = '#57534e'
const CHART_HEIGHT = 240
const monthLabel = new Intl.DateTimeFormat('en-IN', { month: 'short', year: '2-digit' })

function labelOf(month: string): string {
  const [year, monthNumber] = month.split('-').map(Number)
  return monthLabel.format(new Date(year, monthNumber - 1, 1))
}

type TooltipProps = { active?: boolean; payload?: ReadonlyArray<{ value?: unknown }>; label?: unknown }

function TrendTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length || payload[0].value == null) return null
  return (
    <div className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm shadow-md">
      <p className="text-stone-500">{String(label)}</p>
      <p className="font-semibold text-stone-900">{formatPercent(Number(payload[0].value))} average</p>
    </div>
  )
}

export default function CompletionTrendChart({ points }: { points: TrendPoint[] }) {
  const data = points.map((point) => ({ label: labelOf(point.month), value: point.average_completion_percent }))

  return (
    <figure>
      <div className="w-full" role="img" aria-label="Line chart of average completion over the last 12 months. Exact values are in the table below.">
        <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
            <CartesianGrid stroke={GRID_COLOR} vertical={false} />
            <XAxis dataKey="label" tick={{ fill: AXIS_TEXT_COLOR, fontSize: 12 }} tickLine={false} axisLine={{ stroke: GRID_COLOR }} minTickGap={16} />
            <YAxis
              domain={[0, 100]}
              ticks={[0, 25, 50, 75, 100]}
              tickFormatter={(value: number) => `${value}%`}
              tick={{ fill: AXIS_TEXT_COLOR, fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              width={44}
            />
            <Tooltip
              content={({ active, payload, label }) => <TrendTooltip active={active} payload={payload} label={label} />}
              cursor={{ stroke: GRID_COLOR, strokeWidth: 2 }}
            />
            <Line
              type="linear"
              dataKey="value"
              stroke={SERIES_HEX}
              strokeWidth={2}
              dot={{ r: 4, fill: SERIES_HEX, stroke: '#ffffff', strokeWidth: 2 }}
              activeDot={{ r: 6, fill: SERIES_HEX, stroke: '#ffffff', strokeWidth: 2 }}
              connectNulls={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <details className="mt-2 text-sm">
        <summary className="cursor-pointer text-stone-600 hover:text-stone-900">Show as table</summary>
        <table className="mt-2 w-full text-left">
          <thead className="text-xs text-stone-500 uppercase">
            <tr>
              <th scope="col" className="py-1">Month</th>
              <th scope="col" className="py-1 text-right">Average completion</th>
              <th scope="col" className="py-1 text-right">Projects</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {points.map((point) => (
              <tr key={point.month}>
                <td className="py-1">{labelOf(point.month)}</td>
                <td className="py-1 text-right">
                  {point.average_completion_percent === null ? '—' : formatPercent(point.average_completion_percent)}
                </td>
                <td className="py-1 text-right">{point.project_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  )
}
