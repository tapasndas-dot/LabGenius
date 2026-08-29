import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './auth/AuthContext.tsx'
import { BrowserRouter } from 'react-router-dom'
import { CapabilityProvider } from './auth/CapabilityContext.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <CapabilityProvider><BrowserRouter><App /></BrowserRouter></CapabilityProvider>
    </AuthProvider>
  </StrictMode>,
)
