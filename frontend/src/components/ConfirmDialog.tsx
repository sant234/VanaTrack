/**
 * "Are you sure?" dialog for destructive actions.
 * Uses the browser's built-in <dialog>, which already traps keyboard focus and closes on Escape.
 */
import { TriangleAlert } from 'lucide-react'
import { useEffect, useRef, type ReactNode } from 'react'

import Button from './Button'

type ConfirmDialogProps = {
  open: boolean
  title: string
  children: ReactNode
  confirmLabel: string
  isConfirming?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export default function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  isConfirming = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  // Keep the real <dialog> element in sync with the `open` prop.
  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="confirm-dialog-title"
      onCancel={(event) => {
        event.preventDefault() // let React state decide when it closes
        if (!isConfirming) onCancel()
      }}
      className="m-auto w-[min(28rem,calc(100%-2rem))] rounded-2xl bg-white p-0 shadow-xl backdrop:bg-stone-900/50"
    >
      <div className="p-6">
        <div className="flex items-start gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-700">
            <TriangleAlert aria-hidden className="size-5" />
          </span>
          <div>
            <h2 id="confirm-dialog-title" className="text-lg font-bold text-stone-900">
              {title}
            </h2>
            <div className="mt-1 text-sm text-stone-600">{children}</div>
          </div>
        </div>
        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="secondary" onClick={onCancel} disabled={isConfirming}>
            Cancel
          </Button>
          <Button
            onClick={onConfirm}
            isLoading={isConfirming}
            className="bg-red-700 hover:bg-red-800 focus-visible:outline-red-600"
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </dialog>
  )
}
