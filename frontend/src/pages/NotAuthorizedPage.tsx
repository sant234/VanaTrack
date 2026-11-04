import { ShieldX } from 'lucide-react'
import { Link } from 'react-router-dom'

/** Shown when a logged-in user opens a page their role cannot use. */
export default function NotAuthorizedPage() {
  return (
    <section className="flex flex-col items-center rounded-2xl border border-stone-200 bg-white px-6 py-14 text-center">
      <ShieldX aria-hidden className="size-10 text-red-600" />
      <h1 className="mt-3 text-xl font-bold text-stone-900">Not authorized</h1>
      <p className="mt-1 max-w-sm text-sm text-stone-500">Your role does not have access to this page.</p>
      <Link to="/" className="mt-5 text-sm font-semibold text-forest-700 hover:underline">
        Back to dashboard
      </Link>
    </section>
  )
}
