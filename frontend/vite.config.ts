import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, Vite serves React on :5173 and forwards /api to Flask on :8000,
// so the browser still sees a single origin (just like in production).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": "http://localhost:8000" },
  },
});
