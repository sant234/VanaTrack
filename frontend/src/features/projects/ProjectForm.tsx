/** The one form used for both "New project" and "Edit project". */
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import Alert from '../../components/Alert'
import Button from '../../components/Button'
import SelectField from '../../components/SelectField'
import TextAreaField from '../../components/TextAreaField'
import TextField from '../../components/TextField'
import { ApiError } from '../../lib/api'
import { SUGGESTED_UNITS } from './projectLabels'
import {
  toProjectInput,
  validateProjectForm,
  type ProjectFormErrors,
  type ProjectFormField,
  type ProjectFormValues,
} from './projectFormValues'
import type { ProjectInput, ProjectOptions, ProjectStatus, ProjectType } from './types'

type ProjectFormProps = {
  initialValues: ProjectFormValues
  options: ProjectOptions
  submitLabel: string
  cancelTo: string
  onSubmit: (input: ProjectInput) => Promise<unknown>
}

export default function ProjectForm({ initialValues, options, submitLabel, cancelTo, onSubmit }: ProjectFormProps) {
  const [values, setValues] = useState(initialValues)
  const [errors, setErrors] = useState<ProjectFormErrors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  function setField(field: ProjectFormField, value: string) {
    setValues((current) => ({ ...current, [field]: value }))
  }

  /** Changing the type pre-fills its usual unit, unless the user already typed their own. */
  function changeType(type: ProjectType | '') {
    setValues((current) => {
      const unitIsSuggestion = !current.unit || current.unit === (current.type && SUGGESTED_UNITS[current.type])
      const unit = unitIsSuggestion && type ? SUGGESTED_UNITS[type] : current.unit
      return { ...current, type, unit }
    })
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError(null)
    const clientErrors = validateProjectForm(values)
    setErrors(clientErrors)
    if (Object.keys(clientErrors).length > 0) {
      setFormError('Please fix the highlighted fields.')
      return
    }

    setIsSubmitting(true)
    try {
      await onSubmit(toProjectInput(values))
    } catch (error) {
      if (error instanceof ApiError && Object.keys(error.fields).length > 0) {
        setErrors(error.fields as ProjectFormErrors)
        setFormError('Please fix the highlighted fields.')
      } else {
        setFormError(error instanceof ApiError ? error.message : 'Something went wrong. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const stateOptions = options.states.map((state) => ({ value: state, label: state }))

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      {formError && <Alert>{formError}</Alert>}

      <fieldset className="space-y-4 rounded-2xl border border-stone-200 bg-white p-5">
        <legend className="px-1 text-sm font-semibold text-stone-900">About the project</legend>
        <TextField
          label="Project name"
          value={values.name}
          onChange={(event) => setField('name', event.target.value)}
          error={errors.name}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            label="Type"
            placeholder="Choose a type"
            options={options.types}
            value={values.type}
            onChange={(event) => changeType(event.target.value as ProjectType | '')}
            error={errors.type}
          />
          <SelectField
            label="Status"
            options={options.statuses}
            value={values.status}
            onChange={(event) => setField('status', event.target.value as ProjectStatus)}
            error={errors.status}
          />
        </div>
        <TextAreaField
          label="Description (optional)"
          value={values.description}
          onChange={(event) => setField('description', event.target.value)}
          error={errors.description}
        />
      </fieldset>

      <fieldset className="space-y-4 rounded-2xl border border-stone-200 bg-white p-5">
        <legend className="px-1 text-sm font-semibold text-stone-900">Target</legend>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label="Target amount"
            inputMode="numeric"
            placeholder="1000"
            value={values.target_value}
            onChange={(event) => setField('target_value', event.target.value)}
            error={errors.target_value}
          />
          <TextField
            label="Unit"
            placeholder="trees"
            hint="What you are counting, e.g. trees, kL water, kW."
            value={values.unit}
            onChange={(event) => setField('unit', event.target.value)}
            error={errors.unit}
          />
        </div>
        <TextField
          label="Budget in ₹ (optional)"
          inputMode="decimal"
          placeholder="250000"
          value={values.budget_inr}
          onChange={(event) => setField('budget_inr', event.target.value)}
          error={errors.budget_inr}
        />
      </fieldset>

      <fieldset className="space-y-4 rounded-2xl border border-stone-200 bg-white p-5">
        <legend className="px-1 text-sm font-semibold text-stone-900">Where and when</legend>
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            label="State"
            placeholder="Choose a state"
            options={stateOptions}
            value={values.state}
            onChange={(event) => setField('state', event.target.value)}
            error={errors.state}
          />
          <TextField
            label="District (optional)"
            value={values.district}
            onChange={(event) => setField('district', event.target.value)}
            error={errors.district}
          />
          <TextField
            label="Start date"
            type="date"
            value={values.start_date}
            onChange={(event) => setField('start_date', event.target.value)}
            error={errors.start_date}
          />
          <TextField
            label="End date"
            type="date"
            min={values.start_date || undefined}
            value={values.end_date}
            onChange={(event) => setField('end_date', event.target.value)}
            error={errors.end_date}
          />
        </div>
      </fieldset>

      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Link
          to={cancelTo}
          className="inline-flex min-h-10 items-center justify-center rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm font-semibold text-stone-800 hover:bg-stone-100"
        >
          Cancel
        </Link>
        <Button type="submit" isLoading={isSubmitting}>
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}
