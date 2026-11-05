import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate, type Location } from 'react-router-dom'

import Alert from '../../components/Alert'
import Button from '../../components/Button'
import TextField from '../../components/TextField'
import { ApiError } from '../../lib/api'
import AuthPageShell from './AuthPageShell'
import { useAuth } from './useAuth'
import { emailProblem, onlyErrors } from './validation'

type LoginField = 'email' | 'password'

/** Where to go after login: the page the user originally asked for, or the dashboard. */
function redirectTarget(state: unknown): string {
  const from = (state as { from?: Location } | null)?.from
  return from ? `${from.pathname}${from.search}` : '/'
}

export default function LoginPage() {
  const { status, login, sessionExpired } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<LoginField, string>>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (status === 'authenticated') {
    return <Navigate to={redirectTarget(location.state)} replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError(null)

    const errors = onlyErrors({ email: emailProblem(email), password: password ? undefined : 'Password is required.' })
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setIsSubmitting(true)
    try {
      await login({ email: email.trim(), password })
      navigate(redirectTarget(location.state), { replace: true })
    } catch (error) {
      if (error instanceof ApiError && Object.keys(error.fields).length > 0) {
        setFieldErrors(error.fields)
      } else {
        setFormError(error instanceof ApiError ? error.message : 'Something went wrong. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthPageShell title="Log in" subtitle="Track every project, every site, every update.">
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {sessionExpired && !formError && <Alert tone="info">Your session ended. Please log in again.</Alert>}
        {formError && <Alert>{formError}</Alert>}
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          error={fieldErrors.email}
        />
        <TextField
          label="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={fieldErrors.password}
        />
        <Button type="submit" isLoading={isSubmitting} className="w-full">
          Log in
        </Button>
      </form>
      <p className="mt-5 text-center text-sm text-stone-600">
        New here?{' '}
        <Link to="/register" className="inline-flex min-h-10 items-center font-semibold text-forest-700 hover:underline">
          Create an account
        </Link>
      </p>
    </AuthPageShell>
  )
}
