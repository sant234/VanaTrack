const FULL = 100

/** A horizontal bar. The fill stops at 100% visually, but the label shows the real value (e.g. 112%). */
export default function ProgressBar({ percent, label }: { percent: number; label: string }) {
  const width = Math.min(Math.max(percent, 0), FULL)
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuenow={percent}
      aria-valuemin={0}
      aria-valuemax={FULL}
      className="h-2 w-full overflow-hidden rounded-full bg-stone-200"
    >
      {/* Inline style is the one exception to "Tailwind only": the width is a runtime value. */}
      <div className="h-full rounded-full bg-forest-500 transition-[width]" style={{ width: `${width}%` }} />
    </div>
  )
}
