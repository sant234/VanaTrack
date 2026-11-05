import { createContext } from 'react'

export type ToastTone = 'success' | 'error' | 'info'

export type Toast = { id: number; tone: ToastTone; message: string }

export type ToastContextValue = {
  /** Show a short message in the corner of the screen. It hides itself after a few seconds. */
  showToast: (tone: ToastTone, message: string) => void
}

export const ToastContext = createContext<ToastContextValue | null>(null)
