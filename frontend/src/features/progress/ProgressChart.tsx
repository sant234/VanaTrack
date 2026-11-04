/**
 * Running total over time, with the target as a reference line.
 *
 * Chart choices (see the data-visualisation guidelines): one series, so no legend box (the heading names it);
 * dates on a true time scale; a 2px line with visible markers; solid hairline grid; the target is the only dashed line, because it is a
 * threshold; a crosshair tooltip; the same data is also listed in full in the history timeline beside it.
 */
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { formatNumber, formatTimestampDate, toDateInput } from '../../lib/format'
import type { ProgressUpdate } from './types'

// Colours from the theme. The line colour (#3f8f55, forest-500) passed the palette validator on white.
const LINE_COLOR = '#3f8f55'
const TARGET_COLOR = '#78716c' // stone-500, neutral: the target is a reference, not data
const GRID_COLOR = '#e7e5e4' // stone-200
const AXIS_TEXT_COLOR = '#57534e' // stone-600
const CHART_HEIGHT = 260
const Y_HEADROOM = 1.1 // keep the target line clear of the top edge

/** x is a real moment in time (milliseconds), so points sit at their true dates, not evenly spaced. */
type ChartPoint = { time: number; total: number }

/** Oldest first, starting from 0 on the project's start date so the climb is visible. */
function toChartPoints(history: ProgressUpdate[], startDate: string): ChartPoint[] {
  const [year, month, day] = startDate.split('-').map(Number)
  const oldestFirst = [...history].reverse()
  return [
    { time: new Date(year, month - 1, day).getTime(), total: 0 },
    ...oldestFirst.map((entry) => ({ time: new Date(entry.recorded_at).getTime(), total: entry.value })),
  ]
}

const formatTime = (time: number) => formatTimestampDate(new Date(time).toISOString())

type ChartTooltipProps = {
  active?: boolean
  payload?: ReadonlyArray<{ value?: unknown }>
  label?: unknown
  unit: string
}

function ChartTooltip({ active, payload, label, unit }: ChartTooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm shadow-md">
      <p className="text-stone-500">{formatTime(Number(label))}</p>
      <p className="font-semibold text-stone-900">
        {formatNumber(Number(payload[0].value))} {unit}
      </p>
    </div>
  )
}

export default function ProgressChart({
  history,
  startDate,
  targetValue,
  unit,
}: {
  history: ProgressUpdate[]
  startDate: string
  targetValue: number
  unit: string
}) {
  const points = toChartPoints(history, startDate)
  const highest = Math.max(targetValue, ...points.map((point) => point.total))
  const latest = history[0]

  return (
    <figure>
      <div className="h-[260px] w-full" role="img" aria-label={`Line chart of ${unit} over time. Latest total ${formatNumber(latest.value)} of a ${formatNumber(targetValue)} target, logged ${toDateInput(new Date(latest.recorded_at))}.`}>
        <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
          <LineChart data={points} margin={{ top: 16, right: 16, bottom: 4, left: 4 }}>
            <CartesianGrid stroke={GRID_COLOR} vertical={false} />
            <XAxis
              dataKey="time"
              type="number"
              scale="time"
              domain={['dataMin', 'dataMax']}
              tickFormatter={formatTime}
              tick={{ fill: AXIS_TEXT_COLOR, fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: GRID_COLOR }}
              minTickGap={32}
            />
            <YAxis
              domain={[0, Math.ceil(highest * Y_HEADROOM)]}
              tickFormatter={(value: number) => formatNumber(value)}
              tick={{ fill: AXIS_TEXT_COLOR, fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              width={56}
            />
            <ReferenceLine
              y={targetValue}
              stroke={TARGET_COLOR}
              strokeDasharray="6 4"
              label={{ value: `Target ${formatNumber(targetValue)}`, position: 'insideTopRight', fill: AXIS_TEXT_COLOR, fontSize: 12 }}
            />
            <Tooltip
              content={({ active, payload, label }) => (
                <ChartTooltip active={active} payload={payload} label={label} unit={unit} />
              )}
              cursor={{ stroke: GRID_COLOR, strokeWidth: 2 }}
            />
            <Line
              type="linear"
              dataKey="total"
              stroke={LINE_COLOR}
              strokeWidth={2}
              dot={{ r: 4, fill: LINE_COLOR, stroke: '#ffffff', strokeWidth: 2 }}
              activeDot={{ r: 6, fill: LINE_COLOR, stroke: '#ffffff', strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="mt-2 text-xs text-stone-500">
        Running total of {unit}. Dashed line: target. Every update is listed in the history.
      </figcaption>
    </figure>
  )
}
