/** The "Log progress" dialog: enter the new running total, see a live preview, explain any decrease. */
import { useId, useState, type FormEvent } from 'react'

import Alert from '../../components/Alert'
import Button from '../../components/Button'
import Modal from '../../components/Modal'
import TextAreaField from '../../components/TextAreaField'
import TextField from '../../components/TextField'
import { ApiError } from '../../lib/api'
import { formatNumber, formatPercent, formatSignedNumber } from '../../lib/format'
import {
  CORRECTION_NOTE_MIN_LENGTH,
  isDecrease,
  previewOf,
  toProgressInput,
  validateProgressForm,
  type ProgressContext,
  type ProgressFormErrors,
  type ProgressFormValues,
} from './progressForm'
import { useLogProgress } from './useProgress'

type LogProgressDialogProps = {
  open: boolean
  projectId: number
  context: ProgressContext
  onClose: () => void
  onSaved: (message: string) => void
}

/** Server rule codes that belong next to a specific field rather than at the top of the form. */
const CODE_TO_FIELD: Record<string, keyof ProgressFormErrors> = {
  PROGRESS_DECREASE_REQUIRES_NOTE: 'is_correction',
  PROGRESS_NO_CHANGE: 'value',
  PROGRESS_UNREALISTIC: 'value',
}

function Preview({ values, context }: { values: ProgressFormValues; context: ProgressContext }) {
  const preview = previewOf(values, context)
  if (!preview || preview.change === 0) return null
  const changeColor = preview.change > 0 ? 'text-forest-700' : 'text-red-700'
  return (
    <p className="rounded-lg bg-stone-100 px-3 py-2 text-sm text-stone-700" aria-live="polite">
      <span className="font-semibold text-stone-900">
        {formatNumber(preview.from)} → {formatNumber(preview.to)}
      </span>{' '}
      <span className={`font-semibold ${changeColor}`}>({formatSignedNumber(preview.change)})</span>
      {' · '}
      {formatPercent(preview.percent)} of target
      {preview.percent > 100 && <span className="font-semibold text-forest-700"> · exceeds target</span>}
    </p>
  )
}

export default function LogProgressDialog({ open, projectId, context, onClose, onSaved }: LogProgressDialogProps) {
  const titleId = useId()
  const logProgress = useLogProgress(projectId)
  const [values, setValues] = useState<ProgressFormValues>({
    value: '',
    date: context.today,
    isCorrection: false,
    note: '',
  })
  const [errors, setErrors] = useState<ProgressFormErrors>({})
  const [formError, setFormError] = useState<string | null>(null)

  const goingDown = isDecrease(values, context)

  function update<K extends keyof ProgressFormValues>(field: K, value: ProgressFormValues[K]) {
    setValues((current) => ({ ...current, [field]: value }))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError(null)
    const clientErrors = validateProgressForm(values, context)
    setErrors(clientErrors)
    if (Object.keys(clientErrors).length > 0) return

    try {
      const saved = await logProgress.mutateAsync(toProgressInput(values, context))
      onSaved(
        `Progress saved: ${formatNumber(saved.previous_value)} → ${formatNumber(saved.value)} ${context.unit}.`,
      )
    } catch (error) {
      if (!(error instanceof ApiError)) {
        setFormError('Something went wrong. Please try again.')
      } else if (Object.keys(error.fields).length > 0) {
        const { recorded_at: dateError, ...otherFields } = error.fields
        setErrors({ ...otherFields, ...(dateError ? { date: dateError } : {}) })
      } else if (CODE_TO_FIELD[error.code]) {
        setErrors({ [CODE_TO_FIELD[error.code]]: error.message })
      } else {
        setFormError(error.message)
      }
    }
  }

  return (
    <Modal open={open} labelledBy={titleId} onClose={onClose} busy={logProgress.isPending}>
      <form onSubmit={handleSubmit} noValidate className="space-y-4 p-6">
        <div>
          <h2 id={titleId} className="text-lg font-bold text-stone-900">
            Log progress
          </h2>
          <p className="mt-1 text-sm text-stone-600">
            Current total: <span className="font-semibold text-stone-900">{formatNumber(context.currentValue)}</span>{' '}
            of {formatNumber(context.targetValue)} {context.unit}
          </p>
        </div>

        {formError && <Alert>{formError}</Alert>}

        <TextField
          label={`New total (${context.unit} so far)`}
          hint="Enter the running total, not just the amount added since last time."
          inputMode="numeric"
          autoFocus
          value={values.value}
          onChange={(event) => update('value', event.target.value)}
          error={errors.value}
        />

        <Preview values={values} context={context} />

        <TextField
          label="Date of count"
          type="date"
          max={context.today}
          min={context.latestUpdateDate ?? context.startDate}
          value={values.date}
          onChange={(event) => update('date', event.target.value)}
          error={errors.date}
        />

        {(goingDown || values.isCorrection) && (
          <div className="space-y-1 rounded-lg border border-amber-300 bg-amber-50 p-3">
            <label className="flex items-start gap-2 text-sm font-medium text-stone-900">
              <input
                type="checkbox"
                checked={values.isCorrection}
                onChange={(event) => update('isCorrection', event.target.checked)}
                aria-invalid={Boolean(errors.is_correction)}
                className="mt-0.5 size-4 accent-forest-700"
              />
              This is a correction (the total is going down)
            </label>
            <p className="text-xs text-stone-600">
              Totals only go down to fix a mistake or record losses, such as saplings that did not survive.
            </p>
            {errors.is_correction && <p className="text-sm text-red-700">{errors.is_correction}</p>}
          </div>
        )}

        <TextAreaField
          label={values.isCorrection ? `Reason for the correction (at least ${CORRECTION_NOTE_MIN_LENGTH} characters)` : 'Note (optional)'}
          placeholder={values.isCorrection ? 'e.g. 50 saplings died; recounted the site' : ''}
          value={values.note}
          onChange={(event) => update('note', event.target.value)}
          error={errors.note}
        />

        <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
          <Button variant="secondary" onClick={onClose} disabled={logProgress.isPending}>
            Cancel
          </Button>
          <Button type="submit" isLoading={logProgress.isPending}>
            Save progress
          </Button>
        </div>
      </form>
    </Modal>
  )
}
