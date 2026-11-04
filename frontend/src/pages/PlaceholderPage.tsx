import { Sprout } from 'lucide-react'

/** Stand-in for pages that later prompts will build. */
export default function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <section>
      <h1 className="text-2xl font-bold text-stone-900">{title}</h1>
      <div className="mt-6 flex flex-col items-center rounded-2xl border border-dashed border-stone-300 bg-white px-6 py-14 text-center">
        <Sprout aria-hidden className="size-10 text-forest-500" />
        <p className="mt-3 font-semibold text-stone-800">Coming soon</p>
        <p className="mt-1 max-w-sm text-sm text-stone-500">{description}</p>
      </div>
    </section>
  )
}
