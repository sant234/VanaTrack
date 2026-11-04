/**
 * Client-side checks that mirror the backend rules (backend/app/schemas/auth.py).
 * They give instant feedback; the server still checks everything again.
 */

export const PASSWORD_MIN_LENGTH = 8
export const PASSWORD_MAX_BYTES = 72
export const NAME_MIN_LENGTH = 2
export const NAME_MAX_LENGTH = 100

// Deliberately simple: "something@something.something". The server does the strict check.
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export const PASSWORD_HINT = `At least ${PASSWORD_MIN_LENGTH} characters, with a letter and a number.`

export function emailProblem(email: string): string | undefined {
  if (!email.trim()) return 'Email is required.'
  if (!EMAIL_PATTERN.test(email.trim())) return 'Enter a valid email address.'
  return undefined
}

export function nameProblem(name: string): string | undefined {
  const trimmed = name.trim()
  if (trimmed.length < NAME_MIN_LENGTH) return `Name must be at least ${NAME_MIN_LENGTH} characters.`
  if (trimmed.length > NAME_MAX_LENGTH) return `Name must be at most ${NAME_MAX_LENGTH} characters.`
  return undefined
}

export function newPasswordProblem(password: string): string | undefined {
  if (password.length < PASSWORD_MIN_LENGTH) {
    return `Password must be at least ${PASSWORD_MIN_LENGTH} characters.`
  }
  if (new TextEncoder().encode(password).length > PASSWORD_MAX_BYTES) {
    return `Password must be at most ${PASSWORD_MAX_BYTES} characters.`
  }
  if (!/\p{L}/u.test(password)) return 'Password must contain at least one letter.'
  if (!/\p{Nd}/u.test(password)) return 'Password must contain at least one number.'
  return undefined
}

/** Keep only the errors that are actually set, so "no errors" is an empty object. */
export function onlyErrors<T extends string>(errors: Record<T, string | undefined>): Partial<Record<T, string>> {
  return Object.fromEntries(Object.entries(errors).filter(([, message]) => message)) as Partial<Record<T, string>>
}
