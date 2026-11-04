import type { ReactNode } from 'react'

const FULL = 100

/**
 * One horizontal bar with its label above and its value printed beside it (direct labels: the
 * value never depends on hover or colour). Bars stop at 100% width; the printed value can go higher.
 */
export default function BarRow({
  label,
  percent,
  barClass,
  value,
}: {
  label: ReactNode
  percent: number
  barClass: string
  value: ReactNode
}) {
  const width = Math.min(Math.max(percent, 0), FULL)
  return (
    <li className="space-y-1">
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="min-w-0 truncate text-stone-800">{label}</span>
        <span className="shrink-0 text-stone-600">{value}</span>
      </div>
      <div className="h-2 w-full rounded-full bg-stone-100" aria-hidden>
        {/* Inline width is the one exception to "Tailwind only": it is a runtime value. */}
        <div className={`h-full rounded-full ${barClass}`} style={{ width: `${width}%` }} />
      </div>
    </li>
  )
}
