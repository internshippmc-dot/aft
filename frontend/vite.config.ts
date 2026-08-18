import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    watch: {
      // Docker Desktop bind mounts on Windows don't reliably emit native fs
      // events into the container — chokidar needs polling to see edits.
      usePolling: true,
      interval: 300,
    },
  },
});
