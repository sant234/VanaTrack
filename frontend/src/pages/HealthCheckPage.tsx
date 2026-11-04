/**
 * Temporary page for Prompt 0: proves the browser can reach the API, and the API can reach the database.
 * It will be replaced by the dashboard in later prompts.
 */
import { useQuery } from '@tanstack/react-query'
import { CircleCheck, CircleX, Leaf, LoaderCircle, RefreshCw } from 'lucide-react'

import { ApiError, apiRequest } from '../lib/api'

type HealthResponse = { status: string; database: string }

type CheckState = 'loading' | 'ok' | 'down'

const SERVICE_UNAVAILABLE = 503
const AUTO_REFRESH_MS = 10_000

function fetchHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>('/health')
}

/** Work out the API and database state from the query result. */
function deriveStates(isLoading: boolean, data: HealthResponse | undefined, error: unknown) {
  if (isLoading) {
    return { api: 'loading', database: 'loading' } as const
  }
  if (data) {
    return { api: 'ok', database: data.database === 'ok' ? 'ok' : 'down' } as const
  }
  // A 503 means the API answered but told us the database is unreachable.
  const apiAnswered = error instanceof ApiError && error.status === SERVICE_UNAVAILABLE
  return { api: apiAnswered ? 'ok' : 'down', database: 'down' } as const
}

function StatusRow({ label, state }: { label: string; state: CheckState }) {
  const styles = {
    loading: { text: 'Checking…', color: 'text-stone-500', Icon: LoaderCircle, spin: 'animate-spin' },
    ok: { text: 'Connected', color: 'text-forest-700', Icon: CircleCheck, spin: '' },
    down: { text: 'Unreachable', color: 'text-red-700', Icon: CircleX, spin: '' },
  }[state]

  return (
    <li className="flex items-center justify-between gap-4 rounded-lg border border-stone-200 bg-white px-4 py-3">
      <span className="font-medium">{label}</span>
      <span className={`flex items-center gap-2 text-sm font-semibold ${styles.color}`}>
        <styles.Icon aria-hidden className={`size-5 ${styles.spin}`} />
        {styles.text}
      </span>
    </li>
  )
}

export default function HealthCheckPage() {
  const { data, error, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    retry: false,
    refetchInterval: AUTO_REFRESH_MS,
  })

  const states = deriveStates(isLoading, data, error)
  const errorMessage = error instanceof ApiError && error.status !== SERVICE_UNAVAILABLE ? error.message : null

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-10">
      <div className="mb-6 flex items-center gap-3">
        <span className="flex size-11 items-center justify-center rounded-xl bg-forest-700 text-white">
          <Leaf aria-hidden className="size-6" />
        </span>
        <div>
          <h1 className="text-2xl font-bold text-forest-900">VanaTrack</h1>
          <p className="text-sm text-stone-500">System status</p>
        </div>
      </div>

      <ul className="space-y-3" aria-live="polite">
        <StatusRow label="API server" state={states.api} />
        <StatusRow label="Database" state={states.database} />
      </ul>

      {errorMessage && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800">
          {errorMessage}
        </p>
      )}

      <button
        type="button"
        onClick={() => refetch()}
        disabled={isFetching}
        className="mt-6 inline-flex items-center justify-center gap-2 rounded-lg bg-forest-700 px-4 py-2.5 font-semibold text-white hover:bg-forest-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forest-500 disabled:opacity-60"
      >
        <RefreshCw aria-hidden className={`size-4 ${isFetching ? 'animate-spin' : ''}`} />
        Check again
      </button>
    </main>
  )
}
