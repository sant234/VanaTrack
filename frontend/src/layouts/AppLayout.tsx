/**
 * The frame around every logged-in page.
 * Desktop (lg and up): fixed sidebar on the left.  Mobile: a menu button opens a slide-in drawer.
 */
import { Leaf, LogOut, Menu, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'

import Button from '../components/Button'
import RoleBadge from '../features/auth/RoleBadge'
import type { User } from '../features/auth/types'
import { useAuth } from '../features/auth/useAuth'
import { navItemsForRole } from './navigation'

function Brand() {
  return (
    <div className="flex items-center gap-2 px-2">
      <span className="flex size-8 items-center justify-center rounded-lg bg-forest-700 text-white">
        <Leaf aria-hidden className="size-5" />
      </span>
      <span className="text-lg font-bold text-forest-900">VanaTrack</span>
    </div>
  )
}

function NavLinks({ user, onNavigate }: { user: User; onNavigate?: () => void }) {
  return (
    <nav aria-label="Main" className="mt-6 space-y-1">
      {navItemsForRole(user.role).map(({ label, to, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          onClick={onNavigate}
          className={({ isActive }) =>
            `flex min-h-10 items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${
              isActive ? 'bg-forest-100 text-forest-900' : 'text-stone-700 hover:bg-stone-100'
            }`
          }
        >
          <Icon aria-hidden className="size-5" />
          {label}
        </NavLink>
      ))}
    </nav>
  )
}

function MobileDrawer({ user, onClose }: { user: User; onClose: () => void }) {
  // Close with the Escape key, as users expect from any overlay.
  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
      <button type="button" aria-label="Close menu" onClick={onClose} className="absolute inset-0 bg-stone-900/40" />
      <aside className="relative flex h-full w-72 max-w-[85%] flex-col bg-white p-4 shadow-xl">
        <div className="flex items-center justify-between">
          <Brand />
          <button
            type="button"
            onClick={onClose}
            aria-label="Close menu"
            className="flex size-10 items-center justify-center rounded-lg text-stone-600 hover:bg-stone-100"
          >
            <X aria-hidden className="size-5" />
          </button>
        </div>
        <NavLinks user={user} onNavigate={onClose} />
      </aside>
    </div>
  )
}

export default function AppLayout() {
  const { user, logout } = useAuth()
  const location = useLocation()
  // Remember which page the drawer was opened on. Moving to any other page (including via the
  // browser back button) closes it automatically, with no extra effect needed.
  const [drawerOpenedOn, setDrawerOpenedOn] = useState<string | null>(null)
  const isDrawerOpen = drawerOpenedOn === location.pathname
  const openDrawer = () => setDrawerOpenedOn(location.pathname)
  const closeDrawer = () => setDrawerOpenedOn(null)

  if (!user) return null // ProtectedRoute guarantees a user; this only satisfies TypeScript.

  return (
    <div className="min-h-screen lg:flex">
      <aside className="hidden w-64 shrink-0 border-r border-stone-200 bg-white p-4 lg:block">
        <div className="sticky top-4">
          <Brand />
          <NavLinks user={user} />
        </div>
      </aside>

      {isDrawerOpen && <MobileDrawer user={user} onClose={closeDrawer} />}

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-stone-200 bg-white/95 px-4 backdrop-blur lg:px-8">
          <div className="flex items-center gap-2 lg:hidden">
            <button
              type="button"
              onClick={openDrawer}
              aria-label="Open menu"
              aria-expanded={isDrawerOpen}
              className="flex size-10 items-center justify-center rounded-lg text-stone-700 hover:bg-stone-100"
            >
              <Menu aria-hidden className="size-6" />
            </button>
            <Brand />
          </div>
          <div className="ml-auto flex min-w-0 items-center gap-3">
            <div className="hidden min-w-0 text-right sm:block">
              <p className="truncate text-sm font-semibold text-stone-900">{user.name}</p>
              <p className="truncate text-xs text-stone-500">{user.email}</p>
            </div>
            <RoleBadge role={user.role} />
            <Button variant="ghost" onClick={logout} aria-label="Log out" className="px-2 sm:px-3">
              <LogOut aria-hidden className="size-4" />
              <span className="hidden sm:inline">Log out</span>
            </Button>
          </div>
        </header>

        <main className="px-4 py-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
