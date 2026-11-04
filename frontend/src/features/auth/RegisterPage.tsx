import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'

import Alert from '../../components/Alert'
import Button from '../../components/Button'
import TextField from '../../components/TextField'
import { ApiError } from '../../lib/api'
import AuthPageShell from './AuthPageShell'
import { useAuth } from './useAuth'
import { emailProblem, nameProblem, newPasswordProblem, onlyErrors, PASSWORD_HINT } from './validation'

type RegisterField = 'name' | 'email' | 'password' | 'confirmPassword'

export default function RegisterPage() {
  const { status, register } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState<Record<RegisterField, string>>({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<RegisterField, string>>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (status === 'authenticated') {
    return <Navigate to="/" replace />
  }

  function updateField(field: RegisterField, value: string) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  function validate() {
    return onlyErrors({
      name: nameProblem(form.name),
      email: emailProblem(form.email),
      password: newPasswordProblem(form.password),
      confirmPassword: form.password === form.confirmPassword ? undefined : 'Passwords do not match.',
    })
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError(null)

    const errors = validate()
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setIsSubmitting(true)
    try {
      await register({ name: form.name.trim(), email: form.email.trim(), password: form.password })
      navigate('/', { replace: true })
    } catch (error) {
      if (error instanceof ApiError && error.code === 'EMAIL_ALREADY_REGISTERED') {
        setFieldErrors({ email: error.message })
      } else if (error instanceof ApiError && Object.keys(error.fields).length > 0) {
        setFieldErrors(error.fields)
      } else {
        setFormError(error instanceof ApiError ? error.message : 'Something went wrong. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthPageShell title="Create an account" subtitle="New accounts start with view-only access.">
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert>{formError}</Alert>}
        <TextField
          label="Full name"
          autoComplete="name"
          value={form.name}
          onChange={(event) => updateField('name', event.target.value)}
          error={fieldErrors.name}
        />
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          value={form.email}
          onChange={(event) => updateField('email', event.target.value)}
          error={fieldErrors.email}
        />
        <TextField
          label="Password"
          type="password"
          autoComplete="new-password"
          hint={PASSWORD_HINT}
          value={form.password}
          onChange={(event) => updateField('password', event.target.value)}
          error={fieldErrors.password}
        />
        <TextField
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          value={form.confirmPassword}
          onChange={(event) => updateField('confirmPassword', event.target.value)}
          error={fieldErrors.confirmPassword}
        />
        <Button type="submit" isLoading={isSubmitting} className="w-full">
          Create account
        </Button>
      </form>
      <p className="mt-5 text-center text-sm text-stone-600">
        Already have an account?{' '}
        <Link to="/login" className="font-semibold text-forest-700 hover:underline">
          Log in
        </Link>
      </p>
    </AuthPageShell>
  )
}
