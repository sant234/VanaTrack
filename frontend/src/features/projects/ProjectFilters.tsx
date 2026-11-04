import { Search } from 'lucide-react'

import SelectField from '../../components/SelectField'
import type { UserRole } from '../auth/types'
import { SORT_CHOICES, type useProjectFilters } from './useProjectFilters'
import type { ProjectOptions } from './types'

type ProjectFiltersProps = {
  controls: ReturnType<typeof useProjectFilters>
  options: ProjectOptions | undefined
  role: UserRole
}

export default function ProjectFilters({ controls, options, role }: ProjectFiltersProps) {
  const { filters, setFilter } = controls
  const stateOptions = (options?.states ?? []).map((state) => ({ value: state, label: state }))

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
      <div className="relative sm:col-span-2">
        <label htmlFor="project-search" className="sr-only">
          Search projects by name
        </label>
        <Search aria-hidden className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-stone-400" />
        <input
          id="project-search"
          type="search"
          placeholder="Search by name…"
          value={filters.search}
          onChange={(event) => setFilter('search', event.target.value)}
          className="block min-h-10 w-full rounded-lg border border-stone-300 bg-white py-2 pr-3 pl-9 text-stone-900 placeholder:text-stone-400 focus:outline-2 focus:outline-forest-500"
        />
      </div>
      <SelectField
        label="Type"
        hideLabel
        placeholder="All types"
        options={options?.types ?? []}
        value={filters.type}
        onChange={(event) => setFilter('type', event.target.value)}
      />
      <SelectField
        label="Status"
        hideLabel
        placeholder="All statuses"
        options={options?.statuses ?? []}
        value={filters.status}
        onChange={(event) => setFilter('status', event.target.value)}
      />
      <SelectField
        label="State"
        hideLabel
        placeholder="All states"
        options={stateOptions}
        value={filters.state}
        onChange={(event) => setFilter('state', event.target.value)}
      />
      <SelectField
        label="Sort by"
        hideLabel
        options={SORT_CHOICES}
        value={filters.sortChoice}
        onChange={(event) => setFilter('sort_by', event.target.value)}
      />
      {role !== 'viewer' && (
        <label className="flex min-h-10 items-center gap-2 text-sm text-stone-700 sm:col-span-2 xl:col-span-6">
          <input
            type="checkbox"
            checked={filters.mine}
            onChange={(event) => setFilter('mine', event.target.checked ? 'true' : '')}
            className="size-4 rounded border-stone-300 accent-forest-700"
          />
          Only my projects
        </label>
      )}
    </div>
  )
}
