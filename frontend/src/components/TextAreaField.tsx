import { useId, type TextareaHTMLAttributes } from 'react'

type TextAreaFieldProps = TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; error?: string }

export default function TextAreaField({ label, error, className = '', ...textareaProps }: TextAreaFieldProps) {
  const fieldId = useId()
  const errorId = `${fieldId}-error`
  return (
    <div className={className}>
      <label htmlFor={fieldId} className="mb-1 block text-sm font-medium text-stone-700">
        {label}
      </label>
      <textarea
        id={fieldId}
        rows={3}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
        className={`block w-full rounded-lg border bg-white px-3 py-2 text-stone-900 focus:outline-2 focus:outline-offset-0 ${
          error ? 'border-red-500 focus:outline-red-500' : 'border-stone-300 focus:outline-forest-500'
        }`}
        {...textareaProps}
      />
      {error && (
        <p id={errorId} className="mt-1 text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  )
}
