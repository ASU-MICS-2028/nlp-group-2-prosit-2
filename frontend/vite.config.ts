import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  test: {
    // jsdom pretends to be a browser so we can test components without opening one
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
})
