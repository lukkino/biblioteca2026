import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/geist'
import './index.css'
import App from './App.jsx'
import AuthGate from './components/AuthGate.jsx'

// tema salvato applicato subito, così anche la pagina di accesso rispetta il tema scuro
try {
  const saved = localStorage.getItem('theme')
  const dark = saved ? saved === 'dark' : window.matchMedia?.('(prefers-color-scheme: dark)').matches
  document.documentElement.classList.toggle('dark', Boolean(dark))
} catch { /* storage non disponibile */ }

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthGate>
      <App />
    </AuthGate>
  </StrictMode>,
)
