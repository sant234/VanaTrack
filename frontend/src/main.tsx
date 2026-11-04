import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import App from './App.tsx'
import './index.css'
import { queryClient } from './lib/queryClient'

const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('Missing <div id="root"> in index.html')
}

// Providers wrap the whole app: the router handles URLs, the query client handles server data.
createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
