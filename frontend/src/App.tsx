import { Navigate, Route, Routes } from 'react-router-dom'

import LoginPage from './features/auth/LoginPage'
import ProtectedRoute from './features/auth/ProtectedRoute'
import RegisterPage from './features/auth/RegisterPage'
import RoleGate from './features/auth/RoleGate'
import AppLayout from './layouts/AppLayout'
import HealthCheckPage from './pages/HealthCheckPage'
import NotAuthorizedPage from './pages/NotAuthorizedPage'
import PlaceholderPage from './pages/PlaceholderPage'

/** All page routes. Routes inside <ProtectedRoute> require login; <RoleGate> also restricts by role. */
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/status" element={<HealthCheckPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route
            index
            element={<PlaceholderPage title="Dashboard" description="Live stats and charts arrive in Prompt 4." />}
          />
          <Route
            path="projects"
            element={<PlaceholderPage title="Projects" description="Project management arrives in Prompt 2." />}
          />
          <Route
            path="activity"
            element={<PlaceholderPage title="Activity" description="The activity log arrives in Prompt 5." />}
          />
          <Route
            path="users"
            element={
              <RoleGate roles={['admin']} fallback={<NotAuthorizedPage />}>
                <PlaceholderPage title="Users" description="User management arrives in Prompt 6." />
              </RoleGate>
            }
          />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
