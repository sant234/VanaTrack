/** "Are you sure?" dialog for destructive actions. */
import { TriangleAlert } from 'lucide-react'
import { useId, type ReactNode } from 'react'

import Button from './Button'
import Modal from './Modal'

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
  const titleId = useId()
  return (
    <Modal open={open} labelledBy={titleId} onClose={onCancel} busy={isConfirming}>
      <div className="p-6">
        <div className="flex items-start gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-700">
            <TriangleAlert aria-hidden className="size-5" />
          </span>
          <div>
            <h2 id={titleId} className="text-lg font-bold text-stone-900">
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
    </Modal>
  )
}
