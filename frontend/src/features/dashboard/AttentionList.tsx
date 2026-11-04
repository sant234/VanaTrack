/** Projects that need a manager's attention, each linking to its page. */
import { CircleCheck } from 'lucide-react'
import { Link } from 'react-router-dom'

import { formatPercent } from '../../lib/format'
import type { AttentionItem, AttentionReason } from './types'

const REASON_TEXT: Record<AttentionReason, string> = {
  behind_schedule: 'Behind schedule',
  no_recent_update: 'No update in 30+ days',
}

function Reasons({ item }: { item: AttentionItem }) {
  return (
    <div className="flex flex-wrap gap-1">
      {item.reasons.map((reason) => (
        <span
          key={reason}
          className={`rounded-full px-2 py-0.5 text-xs font-semibold whitespace-nowrap ${
            reason === 'behind_schedule' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-900'
          }`}
        >
          {REASON_TEXT[reason]}
        </span>
      ))}
    </div>
  )
}

function lastUpdateText(item: AttentionItem): string {
  if (item.days_since_update === null) return 'Never'
  if (item.days_since_update === 0) return 'Today'
  return `${item.days_since_update} ${item.days_since_update === 1 ? 'day' : 'days'} ago`
}

export default function AttentionList({ items }: { items: AttentionItem[] }) {
  if (items.length === 0) {
    return (
      <p className="flex items-center gap-2 text-sm text-stone-600">
        <CircleCheck aria-hidden className="size-5 text-forest-500" />
        Nothing needs attention right now.
      </p>
    )
  }
  return (
    <>
      {/* Small screens: one card per project. */}
      <ul className="space-y-3 md:hidden">
        {items.map((item) => (
          <li key={item.id} className="rounded-xl border border-stone-200 p-3">
            <Link to={`/projects/${item.id}`} className="font-semibold text-stone-900 hover:text-forest-700 hover:underline">
              {item.name}
            </Link>
            <p className="mt-1 text-sm text-stone-600">
              {formatPercent(item.progress_percent)} done vs {formatPercent(item.expected_percent)} of timeline · last
              update {lastUpdateText(item).toLowerCase()}
            </p>
            <div className="mt-2">
              <Reasons item={item} />
            </div>
          </li>
        ))}
      </ul>
      {/* Medium screens and up: a table. */}
      <table className="hidden w-full text-left text-sm md:table">
        <thead className="border-b border-stone-200 text-xs font-semibold tracking-wide text-stone-500 uppercase">
          <tr>
            <th scope="col" className="py-2 pr-3">Project</th>
            <th scope="col" className="py-2 pr-3">Why</th>
            <th scope="col" className="py-2 pr-3 text-right">Done</th>
            <th scope="col" className="py-2 pr-3 text-right">Timeline passed</th>
            <th scope="col" className="py-2 pr-3">Last update</th>
            <th scope="col" className="py-2">Owner</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-100">
          {items.map((item) => (
            <tr key={item.id}>
              <td className="py-2 pr-3">
                <Link to={`/projects/${item.id}`} className="font-semibold text-stone-900 hover:text-forest-700 hover:underline">
                  {item.name}
                </Link>
              </td>
              <td className="py-2 pr-3">
                <Reasons item={item} />
              </td>
              <td className="py-2 pr-3 text-right font-semibold text-stone-900">{formatPercent(item.progress_percent)}</td>
              <td className="py-2 pr-3 text-right text-stone-600">{formatPercent(item.expected_percent)}</td>
              <td className="py-2 pr-3 whitespace-nowrap text-stone-600">{lastUpdateText(item)}</td>
              <td className="py-2 text-stone-600">{item.owner_name}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
