/**
 * Project list filters, stored in the URL (e.g. /projects?status=active&sort=name&order=asc).
 * The URL is the single source of truth, so refresh, back/forward and shared links keep the filters.
 */
import { useSearchParams } from 'react-router-dom'

import type { ProjectListParams, ProjectSort, SortOrder } from './types'

export const SORT_CHOICES = [
  { value: 'created_at:desc', label: 'Newest first' },
  { value: 'created_at:asc', label: 'Oldest first' },
  { value: 'name:asc', label: 'Name A–Z' },
  { value: 'name:desc', label: 'Name Z–A' },
  { value: 'progress:desc', label: 'Most progress' },
  { value: 'progress:asc', label: 'Least progress' },
  { value: 'end_date:asc', label: 'Ending soonest' },
]
const DEFAULT_SORT = 'created_at:desc'

export const FILTER_KEYS = ['search', 'type', 'status', 'state', 'mine'] as const
type FilterKey = (typeof FILTER_KEYS)[number]

export function useProjectFilters() {
  const [searchParams, setSearchParams] = useSearchParams()

  const sortChoice = searchParams.get('sort_by') ?? DEFAULT_SORT
  const [sort, order] = sortChoice.split(':') as [ProjectSort, SortOrder]

  const filters = {
    search: searchParams.get('search') ?? '',
    type: searchParams.get('type') ?? '',
    status: searchParams.get('status') ?? '',
    state: searchParams.get('state') ?? '',
    mine: searchParams.get('mine') === 'true',
    sortChoice,
  }

  const apiParams: Omit<ProjectListParams, 'search'> = {
    type: filters.type || undefined,
    status: filters.status || undefined,
    state: filters.state || undefined,
    mine: filters.mine || undefined,
    sort,
    order,
  }

  const hasActiveFilters = FILTER_KEYS.some((key) => Boolean(searchParams.get(key)))

  /**
   * Start every change from the address bar itself, not from the last rendered copy of it.
   * Two quick changes (e.g. untick "Only my projects", then pick a sort) can happen before React
   * re-renders; starting from a stale copy would silently undo the first change.
   */
  function latestParams(): URLSearchParams {
    return new URLSearchParams(window.location.search)
  }

  /** Set one filter; an empty value removes it from the URL. replace: typing does not flood history. */
  function setFilter(key: FilterKey | 'sort_by', value: string) {
    const next = latestParams()
    if (value && !(key === 'sort_by' && value === DEFAULT_SORT)) next.set(key, value)
    else next.delete(key)
    setSearchParams(next, { replace: true })
  }

  function clearFilters() {
    const next = latestParams()
    FILTER_KEYS.forEach((key) => next.delete(key))
    setSearchParams(next)
  }

  return { filters, apiParams, hasActiveFilters, setFilter, clearFilters }
}
