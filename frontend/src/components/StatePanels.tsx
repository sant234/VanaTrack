/** The "nothing here" and "something went wrong" panels used by every data view. */
import { CloudOff, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import Button from './Button'

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-stone-300 bg-white px-6 py-12 text-center">
      <Icon aria-hidden className="size-10 text-forest-500" />
      <p className="mt-3 font-semibold text-stone-800">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-stone-500">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center rounded-2xl border border-red-200 bg-red-50 px-6 py-12 text-center"
    >
      <CloudOff aria-hidden className="size-10 text-red-600" />
      <p className="mt-3 font-semibold text-red-900">Could not load data</p>
      <p className="mt-1 max-w-sm text-sm text-red-800">{message}</p>
      <Button variant="secondary" onClick={onRetry} className="mt-5">
        Try again
      </Button>
    </div>
  )
}
