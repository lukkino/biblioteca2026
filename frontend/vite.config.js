import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { execSync } from 'child_process'
import pkg from './package.json' with { type: 'json' }

// Versione mostrata nell'app: unica fonte è il campo "version" di package.json
// (lo legge anche il backend, per /api/health).
function getAppVersion() {
  return pkg.version
}

// Data "ultimo aggiornamento": data dell'ultimo commit. Nella build Docker di Render
// git non c'è: si usa la data della build, che parte subito dopo il push.
function getLastUpdate() {
  try {
    const iso = execSync('git log -1 --format=%cI', { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim()
    if (iso) return iso
  } catch { /* git non disponibile */ }
  return new Date().toISOString()
}

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  define: {
    __APP_VERSION__: JSON.stringify(getAppVersion()),
    __APP_LAST_UPDATE__: JSON.stringify(getLastUpdate()),
  },
})
