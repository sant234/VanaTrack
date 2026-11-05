import type { ReactNode } from 'react'

/**
 * The one small "pill" label used across the app. Each tone has one fixed meaning, so a colour always
 * says the same thing: green = good / on track, red = problem, amber = needs attention, sky = neutral info.
 */
export type BadgeTone = 'success' | 'danger' | 'warning' | 'info' | 'neutral' | 'muted' | 'strong'

const TONE_CLASSES: Record<BadgeTone, string> = {
  success: 'bg-forest-100 text-forest-900',
  danger: 'bg-red-100 text-red-800',
  warning: 'bg-amber-100 text-amber-900',
  info: 'bg-sky-100 text-sky-900',
  neutral: 'bg-stone-200 text-stone-700',
  muted: 'bg-stone-200 text-stone-600',
  strong: 'bg-stone-800 text-white',
}

export default function Badge({ tone, children }: { tone: BadgeTone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold whitespace-nowrap ${TONE_CLASSES[tone]}`}
    >
      {children}
    </span>
  )
}
