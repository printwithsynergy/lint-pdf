import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// 1420 matches the Tauri convention so a future `tauri ios dev` /
// `tauri android dev` shell can pick this up without port surgery.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 1420,
    strictPort: true,
    host: "0.0.0.0",
  },
  preview: {
    port: 1420,
  },
  build: {
    target: "es2022",
    sourcemap: true,
  },
});
