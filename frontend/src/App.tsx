import { Route, Routes } from 'react-router-dom'

import ActivityPage from './features/activity/ActivityPage'
import LoginPage from './features/auth/LoginPage'
import DashboardPage from './features/dashboard/DashboardPage'
import ProtectedRoute from './features/auth/ProtectedRoute'
import RegisterPage from './features/auth/RegisterPage'
import RoleGate from './features/auth/RoleGate'
import EditProjectPage from './features/projects/EditProjectPage'
import NewProjectPage from './features/projects/NewProjectPage'
import ProjectDetailPage from './features/projects/ProjectDetailPage'
import ProjectsListPage from './features/projects/ProjectsListPage'
import UsersAdminPage from './features/users/UsersAdminPage'
import AppLayout from './layouts/AppLayout'
import HealthCheckPage from './pages/HealthCheckPage'
import NotAuthorizedPage from './pages/NotAuthorizedPage'
import NotFoundPage from './pages/NotFoundPage'

/**
 * All page routes. Routes inside <ProtectedRoute> require login; <RoleGate> also restricts by role.
 * Unknown URLs show the 404 page inside the app frame (logged-out visitors are sent to login first).
 */
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/status" element={<HealthCheckPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="projects" element={<ProjectsListPage />} />
          <Route
            path="projects/new"
            element={
              <RoleGate roles={['admin', 'manager']} fallback={<NotAuthorizedPage />}>
                <NewProjectPage />
              </RoleGate>
            }
          />
          <Route path="projects/:projectId" element={<ProjectDetailPage />} />
          <Route path="projects/:projectId/edit" element={<EditProjectPage />} />
          <Route path="activity" element={<ActivityPage />} />
          <Route
            path="users"
            element={
              <RoleGate roles={['admin']} fallback={<NotAuthorizedPage />}>
                <UsersAdminPage />
              </RoleGate>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  )
}
