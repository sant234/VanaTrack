import { useEffect, useRef } from 'react'

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])'

/**
 * While `active`, keep keyboard focus inside the returned element: Tab / Shift+Tab wrap around
 * instead of leaving it, and Escape calls `onEscape`. Used by dialogs and the mobile menu.
 * (A native <dialog> blocks the page behind it, but still lets Tab escape to the browser's own UI.)
 */
export function useFocusTrap<T extends HTMLElement>(active: boolean, onEscape?: () => void) {
  const containerRef = useRef<T>(null)
  // Read the latest callback without re-running the effect (which would move focus) on every render.
  const onEscapeRef = useRef(onEscape)
  useEffect(() => {
    onEscapeRef.current = onEscape
  }, [onEscape])

  useEffect(() => {
    const container = containerRef.current
    if (!active || !container) return
    const focusable = () => Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE))

    // Start inside, unless something inside (e.g. an autoFocus field) already has focus.
    if (!container.contains(document.activeElement)) focusable()[0]?.focus()

    function handleKey(event: KeyboardEvent) {
      if (event.key === 'Escape' && onEscapeRef.current) {
        event.preventDefault()
        onEscapeRef.current()
        return
      }
      if (event.key !== 'Tab') return
      const items = focusable()
      const first = items[0]
      const last = items[items.length - 1]
      const outside = !container?.contains(document.activeElement)
      if (event.shiftKey && (document.activeElement === first || outside)) {
        event.preventDefault()
        last?.focus()
      } else if (!event.shiftKey && (document.activeElement === last || outside)) {
        event.preventDefault()
        first?.focus()
      }
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [active])

  return containerRef
}
