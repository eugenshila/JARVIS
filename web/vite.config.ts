import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const BRIDGE_PORT = Number(process.env.JARVIS_BRIDGE_PORT) || 8787
const BRIDGE_TARGET = `http://127.0.0.1:${BRIDGE_PORT}`

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Honour PORT so a second instance can run alongside the first. The bridge
    // only accepts sockets from localhost:5173-5199, so stay inside that range
    // or set JARVIS_ALLOWED_ORIGINS to match.
    port: Number(process.env.PORT) || 5173,
    // Bind every interface, not just loopback. Locally this changes nothing;
    // it is what lets the page be reached from a phone on the same Wi-Fi, or
    // from the browser when the app runs in a container or remote sandbox.
    host: '0.0.0.0',
    // A remote sandbox serves the page from a hostname Vite cannot know in
    // advance, and its default host check would answer "Blocked request".
    allowedHosts: true,
    /**
     * Same-origin path to the bridge.
     *
     * The browser and the bridge are on the same machine in the normal case, so
     * ws://localhost:8787 works and stays the default. Everywhere else — a
     * remote preview, a tunnel, a phone on the LAN — "localhost" in the page
     * means the *viewer's* machine, not the one running the bridge, and the
     * socket silently never connects. Proxying it through the dev server means
     * one origin for everything: the page, the WebSocket, and the /img, /media
     * and /stt endpoints, which also keeps them inside the page's own CSP.
     */
    proxy: {
      '/bridge': {
        target: BRIDGE_TARGET,
        ws: true,
        changeOrigin: false,
        rewrite: (path) => path.replace(/^\/bridge/, '') || '/',
      },
      // The Python brain, for anything that wants it directly (diagnostics,
      // the legacy dashboard) without a second origin or a CORS round trip.
      '/api/jarvis': {
        target: process.env.JARVIS_API_URL || 'http://127.0.0.1:8000',
        changeOrigin: false,
        rewrite: (path) => path.replace(/^\/api\/jarvis/, '') || '/',
      },
    },
  },
  optimizeDeps: {
    // kokoro-js pulls in `phonemizer`, which carries espeak-ng as inline WASM.
    // Vite's dependency pre-bundler rewrites that initialisation and the
    // language table ends up empty — the symptom is
    // `Invalid language identifier: "en". Should be one of: .` at generate()
    // time, long after the model has loaded successfully. Serving these
    // untouched fixes it.
    exclude: ['kokoro-js', 'phonemizer', '@huggingface/transformers'],
  },
})
