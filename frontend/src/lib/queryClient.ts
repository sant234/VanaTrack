import { QueryClient } from '@tanstack/react-query'

import { ApiError } from './api'

const MAX_RETRIES = 2
const ONE_MINUTE_MS = 60_000

/** Don't retry errors that will never succeed on retry (bad input, not allowed, not found). */
function shouldRetry(failureCount: number, error: unknown): boolean {
  const isClientError = error instanceof ApiError && error.status >= 400 && error.status < 500
  return !isClientError && failureCount < MAX_RETRIES
}

/** Shared cache for all server data. Pages refetch when the tab regains focus, keeping numbers fresh. */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: shouldRetry,
      staleTime: ONE_MINUTE_MS,
      refetchOnWindowFocus: true,
    },
  },
})
