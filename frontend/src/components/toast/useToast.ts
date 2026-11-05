import { useContext } from 'react'

import { ApiError } from '../../lib/api'
import { ToastContext, type ToastContextValue } from './toastContext'

/** Show success / error toasts from anywhere inside <ToastProvider>. */
export function useToast(): ToastContextValue {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used inside <ToastProvider>')
  }
  return context
}

/** The server's own message when it sent one (e.g. a 403 reason), otherwise a generic fallback. */
export function errorMessageOf(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}
