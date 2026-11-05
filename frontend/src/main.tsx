import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import App from './App.tsx'
import ToastProvider from './components/toast/ToastProvider'
import AuthProvider from './features/auth/AuthProvider'
import './index.css'
import { queryClient } from './lib/queryClient'

const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('Missing <div id="root"> in index.html')
}

// Providers wrap the whole app: the query client handles server data,
// toasts show short success/error messages, the auth provider knows who is logged in,
// and the router handles URLs.
createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <AuthProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>
  </StrictMode>,
)
