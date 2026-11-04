/**
 * A centered dialog built on the browser's own <dialog> element, which already traps keyboard
 * focus inside it, dims the page behind it, and closes on Escape.
 */
import { useEffect, useRef, type ReactNode } from 'react'

type ModalProps = {
  open: boolean
  /** id of the element that names the dialog (usually its heading). */
  labelledBy: string
  /** Called on Escape. Ignored while `busy`, so a save in progress cannot be abandoned half-way. */
  onClose: () => void
  busy?: boolean
  children: ReactNode
}

export default function Modal({ open, labelledBy, onClose, busy = false, children }: ModalProps) {
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
      aria-labelledby={labelledBy}
      onCancel={(event) => {
        event.preventDefault() // React state decides when the dialog closes
        if (!busy) onClose()
      }}
      className="m-auto max-h-[calc(100dvh-2rem)] w-[min(30rem,calc(100%-2rem))] overflow-y-auto rounded-2xl bg-white p-0 shadow-xl backdrop:bg-stone-900/50"
    >
      {open && children}
    </dialog>
  )
}
