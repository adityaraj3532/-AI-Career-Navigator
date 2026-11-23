import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
// @ts-expect-error plain JS module
import { apiMiddleware } from './server/advice.mjs'

export default defineConfig(({ mode }) => {
  // Make ANTHROPIC_API_KEY from .env / .env.local available to the backend.
  Object.assign(process.env, loadEnv(mode, process.cwd(), ''))
  return {
    plugins: [
      react(),
      tailwindcss(),
      {
        name: 'pathpilot-api',
        configureServer(server) { server.middlewares.use(apiMiddleware) },
        configurePreviewServer(server) { server.middlewares.use(apiMiddleware) },
      },
    ],
  }
})
