/**
 * Form state for create/edit, its validation (mirrors backend/app/schemas/project.py), and
 * conversion between the form's text inputs and the API's typed body.
 */
import type { Project, ProjectInput, ProjectStatus, ProjectType } from './types'

export const NAME_MIN_LENGTH = 3
export const NAME_MAX_LENGTH = 150
export const DESCRIPTION_MAX_LENGTH = 2000
export const UNIT_MAX_LENGTH = 30
export const DISTRICT_MAX_LENGTH = 60
export const TARGET_MAX_VALUE = 1_000_000_000

/** Every input holds text, exactly as typed; conversion happens once, on submit. */
export type ProjectFormValues = {
  name: string
  description: string
  type: ProjectType | ''
  status: ProjectStatus
  target_value: string
  unit: string
  state: string
  district: string
  start_date: string
  end_date: string
  budget_inr: string
}

export type ProjectFormField = keyof ProjectFormValues
export type ProjectFormErrors = Partial<Record<ProjectFormField, string>>

export const EMPTY_PROJECT_FORM: ProjectFormValues = {
  name: '',
  description: '',
  type: '',
  status: 'planned',
  target_value: '',
  unit: '',
  state: '',
  district: '',
  start_date: '',
  end_date: '',
  budget_inr: '',
}

export function formValuesFromProject(project: Project): ProjectFormValues {
  return {
    name: project.name,
    description: project.description ?? '',
    type: project.type,
    status: project.status,
    target_value: String(project.target_value),
    unit: project.unit,
    state: project.state,
    district: project.district ?? '',
    start_date: project.start_date,
    end_date: project.end_date,
    budget_inr: project.budget_inr === null ? '' : String(project.budget_inr),
  }
}

const WHOLE_NUMBER = /^\d+$/
const MONEY = /^\d+(\.\d{1,2})?$/

function targetProblem(text: string): string | undefined {
  const value = text.trim()
  if (!value) return 'Target is required.'
  if (!WHOLE_NUMBER.test(value)) return 'Enter a whole number, like 1000.'
  const number = Number(value)
  if (number <= 0) return 'Target must be greater than 0.'
  if (number > TARGET_MAX_VALUE) return 'Target is too large.'
  return undefined
}

function budgetProblem(text: string): string | undefined {
  const value = text.trim()
  if (!value) return undefined
  if (!MONEY.test(value)) return 'Enter an amount like 250000 or 250000.50 (no commas or minus sign).'
  return undefined
}

function lengthProblem(text: string, label: string, min: number, max: number): string | undefined {
  const length = text.trim().length
  if (length < min) return min === 1 ? `${label} is required.` : `${label} must be at least ${min} characters.`
  if (length > max) return `${label} must be at most ${max} characters.`
  return undefined
}

export function validateProjectForm(values: ProjectFormValues): ProjectFormErrors {
  const errors: ProjectFormErrors = {
    name: lengthProblem(values.name, 'Name', NAME_MIN_LENGTH, NAME_MAX_LENGTH),
    description:
      values.description.trim().length > DESCRIPTION_MAX_LENGTH
        ? `Description must be at most ${DESCRIPTION_MAX_LENGTH} characters.`
        : undefined,
    type: values.type ? undefined : 'Choose a project type.',
    target_value: targetProblem(values.target_value),
    unit: lengthProblem(values.unit, 'Unit', 1, UNIT_MAX_LENGTH),
    state: values.state ? undefined : 'Choose a state.',
    district:
      values.district.trim().length > DISTRICT_MAX_LENGTH
        ? `District must be at most ${DISTRICT_MAX_LENGTH} characters.`
        : undefined,
    start_date: values.start_date ? undefined : 'Start date is required.',
    end_date: values.end_date ? undefined : 'End date is required.',
    budget_inr: budgetProblem(values.budget_inr),
  }
  // "YYYY-MM-DD" strings compare correctly as text.
  if (values.start_date && values.end_date && values.end_date < values.start_date) {
    errors.end_date = 'End date cannot be before the start date.'
  }
  return Object.fromEntries(Object.entries(errors).filter(([, message]) => message)) as ProjectFormErrors
}

/** Convert validated form text into the API body. Call only after validateProjectForm passes. */
export function toProjectInput(values: ProjectFormValues): ProjectInput {
  const optionalText = (text: string) => text.trim() || null
  return {
    name: values.name.trim(),
    description: optionalText(values.description),
    type: values.type as ProjectType,
    status: values.status,
    target_value: Number(values.target_value.trim()),
    unit: values.unit.trim(),
    state: values.state,
    district: optionalText(values.district),
    start_date: values.start_date,
    end_date: values.end_date,
    budget_inr: values.budget_inr.trim() ? Number(values.budget_inr.trim()) : null,
  }
}
