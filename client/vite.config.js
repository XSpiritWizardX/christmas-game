import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command }) => ({
  plugins: [react()],
  // In production the React client and Flask/Socket.IO server are served
  // from the same Render web service. Keep local development unchanged.
  define:
    command === "build"
      ? {
          "import.meta.env.VITE_SERVER_URL": "window.location.origin"
        }
      : {},
  server: {
    port: 5173
  }
}));
