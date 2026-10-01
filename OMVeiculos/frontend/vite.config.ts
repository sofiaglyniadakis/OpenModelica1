// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Em desenvolvimento, a API (python -m omveiculos) roda em :8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  build: { chunkSizeWarningLimit: 1200 },
});
