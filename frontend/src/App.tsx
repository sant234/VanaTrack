import { Route, Routes } from 'react-router-dom'

import HealthCheckPage from './pages/HealthCheckPage'

/** All page routes live here. Real pages (login, dashboard, projects) arrive in later prompts. */
export default function App() {
  return (
    <Routes>
      <Route path="*" element={<HealthCheckPage />} />
    </Routes>
  )
}
