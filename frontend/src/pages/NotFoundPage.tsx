import { Compass } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useDocumentTitle } from '../lib/useDocumentTitle'

/** Shown for any URL that does not match a page, instead of silently sending the user elsewhere. */
export default function NotFoundPage() {
  useDocumentTitle('Page not found')
  return (
    <section className="flex flex-col items-center rounded-2xl border border-stone-200 bg-white px-6 py-14 text-center">
      <Compass aria-hidden className="size-10 text-forest-500" />
      <p className="mt-3 text-sm font-semibold text-stone-500">404</p>
      <h1 className="mt-1 text-2xl font-bold text-stone-900">Page not found</h1>
      <p className="mt-1 max-w-sm text-sm text-stone-500">The link may be wrong, or the page no longer exists.</p>
      <Link
        to="/"
        className="mt-5 inline-flex min-h-10 items-center rounded-lg px-3 text-sm font-semibold text-forest-700 hover:underline"
      >
        Back to dashboard
      </Link>
    </section>
  )
}
