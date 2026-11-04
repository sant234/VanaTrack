import { useId, type InputHTMLAttributes } from 'react'

type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string
  error?: string
  hint?: string
}

/** A labelled input that shows its error message right underneath, linked for screen readers. */
export default function TextField({ label, error, hint, className = '', ...inputProps }: TextFieldProps) {
  const inputId = useId()
  const hintId = `${inputId}-hint`
  const errorId = `${inputId}-error`
  const describedBy = [hint && hintId, error && errorId].filter(Boolean).join(' ') || undefined

  return (
    <div className={className}>
      <label htmlFor={inputId} className="mb-1 block text-sm font-medium text-stone-700">
        {label}
      </label>
      <input
        id={inputId}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy}
        className={`block min-h-10 w-full rounded-lg border bg-white px-3 py-2 text-stone-900 placeholder:text-stone-400 focus:outline-2 focus:outline-offset-0 ${
          error ? 'border-red-500 focus:outline-red-500' : 'border-stone-300 focus:outline-forest-500'
        }`}
        {...inputProps}
      />
      {hint && !error && (
        <p id={hintId} className="mt-1 text-xs text-stone-500">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="mt-1 text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  )
}
