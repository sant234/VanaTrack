import { Activity, FolderTree, LayoutDashboard, Users, type LucideIcon } from 'lucide-react'

import type { UserRole } from '../features/auth/types'

export type NavItem = {
  label: string
  to: string
  icon: LucideIcon
  /** Roles that see this link. Omit to show it to everyone logged in. */
  roles?: UserRole[]
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', to: '/', icon: LayoutDashboard },
  { label: 'Projects', to: '/projects', icon: FolderTree },
  { label: 'Activity', to: '/activity', icon: Activity },
  { label: 'Users', to: '/users', icon: Users, roles: ['admin'] },
]

export function navItemsForRole(role: UserRole): NavItem[] {
  return NAV_ITEMS.filter((item) => !item.roles || item.roles.includes(role))
}
