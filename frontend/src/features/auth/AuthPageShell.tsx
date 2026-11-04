import { Leaf } from 'lucide-react'
import type { ReactNode } from 'react'

/** Centered card layout shared by the login and register pages. */
export default function AuthPageShell({ title, subtitle, children }: {
  title: string
  subtitle: string
  children: ReactNode
}) {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-3">
          <span className="flex size-11 items-center justify-center rounded-xl bg-forest-700 text-white">
            <Leaf aria-hidden className="size-6" />
          </span>
          <span className="text-2xl font-bold text-forest-900">VanaTrack</span>
        </div>
        <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
          <h1 className="text-xl font-bold text-stone-900">{title}</h1>
          <p className="mt-1 mb-5 text-sm text-stone-500">{subtitle}</p>
          {children}
        </div>
      </div>
    </main>
  )
}
