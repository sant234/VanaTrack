/**
 * Holds the list of visible toasts and draws them in a fixed corner region.
 * Built by hand instead of adding a library: it only needs to show, auto-hide and dismiss messages.
 * The region is a polite live region, so screen readers announce each new message.
 */
import { CircleAlert, CircleCheck, Info, X, type LucideIcon } from 'lucide-react'
import { useCallback, useMemo, useRef, useState, type ReactNode } from 'react'

import { ToastContext, type Toast, type ToastContextValue, type ToastTone } from './toastContext'

const TOAST_DURATION_MS = 5000
// Errors stay longer: they usually explain something the user must act on.
const ERROR_TOAST_DURATION_MS = 8000
const MAX_VISIBLE_TOASTS = 3

const TONE_STYLES: Record<ToastTone, { box: string; Icon: LucideIcon }> = {
  success: { box: 'border-forest-100 bg-forest-50 text-forest-900', Icon: CircleCheck },
  error: { box: 'border-red-200 bg-red-50 text-red-900', Icon: CircleAlert },
  info: { box: 'border-sky-200 bg-sky-50 text-sky-900', Icon: Info },
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: () => void }) {
  const { box, Icon } = TONE_STYLES[toast.tone]
  return (
    <li
      role={toast.tone === 'error' ? 'alert' : 'status'}
      className={`pointer-events-auto flex items-start gap-2 rounded-xl border py-2 pr-1 pl-3 text-sm shadow-lg ${box}`}
    >
      <Icon aria-hidden className="mt-2 size-4 shrink-0" />
      <p className="min-w-0 flex-1 py-1.5 break-words">{toast.message}</p>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss message"
        className="flex size-10 shrink-0 items-center justify-center rounded-lg opacity-70 hover:opacity-100 focus-visible:outline-2 focus-visible:outline-forest-500"
      >
        <X aria-hidden className="size-4" />
      </button>
    </li>
  )
}

export default function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const showToast = useCallback(
    (tone: ToastTone, message: string) => {
      const id = nextId.current++
      setToasts((current) => [...current, { id, tone, message }].slice(-MAX_VISIBLE_TOASTS))
      window.setTimeout(() => dismiss(id), tone === 'error' ? ERROR_TOAST_DURATION_MS : TOAST_DURATION_MS)
    },
    [dismiss],
  )

  const value = useMemo<ToastContextValue>(() => ({ showToast }), [showToast])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ol
        aria-live="polite"
        aria-label="Notifications"
        className="pointer-events-none fixed inset-x-4 bottom-4 z-50 flex flex-col gap-2 sm:left-auto sm:w-96"
      >
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={() => dismiss(toast.id)} />
        ))}
      </ol>
    </ToastContext.Provider>
  )
}
