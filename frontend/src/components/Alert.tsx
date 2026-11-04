import { CircleAlert, Info } from 'lucide-react'
import type { ReactNode } from 'react'

type AlertTone = 'error' | 'info'

const TONE_STYLES: Record<AlertTone, { box: string; Icon: typeof Info }> = {
  error: { box: 'bg-red-50 text-red-800 border-red-200', Icon: CircleAlert },
  info: { box: 'bg-forest-50 text-forest-900 border-forest-100', Icon: Info },
}

/** A message box for form-level errors or notices. Errors are announced to screen readers. */
export default function Alert({ tone = 'error', children }: { tone?: AlertTone; children: ReactNode }) {
  const { box, Icon } = TONE_STYLES[tone]
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={`flex items-start gap-2 rounded-lg border px-3 py-2.5 text-sm ${box}`}
    >
      <Icon aria-hidden className="mt-0.5 size-4 shrink-0" />
      <div>{children}</div>
    </div>
  )
}
