import { useId, type SelectHTMLAttributes } from 'react'

export type SelectOption = { value: string; label: string }

type SelectFieldProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string
  options: SelectOption[]
  error?: string
  /** Shown as the first, empty choice (e.g. "All types" or "Choose a state"). */
  placeholder?: string
  hideLabel?: boolean
}

export default function SelectField({
  label,
  options,
  error,
  placeholder,
  hideLabel = false,
  className = '',
  ...selectProps
}: SelectFieldProps) {
  const selectId = useId()
  const errorId = `${selectId}-error`
  return (
    <div className={className}>
      <label htmlFor={selectId} className={hideLabel ? 'sr-only' : 'mb-1 block text-sm font-medium text-stone-700'}>
        {label}
      </label>
      <select
        id={selectId}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
        className={`block min-h-10 w-full rounded-lg border bg-white px-3 py-2 text-stone-900 focus:outline-2 focus:outline-offset-0 ${
          error ? 'border-red-500 focus:outline-red-500' : 'border-stone-300 focus:outline-forest-500'
        }`}
        {...selectProps}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error && (
        <p id={errorId} className="mt-1 text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  )
}
