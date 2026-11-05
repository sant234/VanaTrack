import { useEffect, useState } from 'react'

/** The current time, refreshed every `intervalMs`, so labels like "5 min ago" keep counting. */
export function useNow(intervalMs: number): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), intervalMs)
    return () => window.clearInterval(timer)
  }, [intervalMs])
  return now
}
