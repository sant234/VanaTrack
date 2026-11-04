export type UserRole = 'admin' | 'manager' | 'viewer'

export type User = {
  id: number
  name: string
  email: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export type LoginInput = { email: string; password: string }

export type RegisterInput = { name: string; email: string; password: string }

export type TokenResponse = {
  access_token: string
  token_type: 'bearer'
  user: User
}
