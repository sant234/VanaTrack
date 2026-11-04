/** A grey pulsing block shown while data loads, roughly the shape of the content to come. */
export default function Skeleton({ className = '' }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded-lg bg-stone-200 ${className}`} />
}
