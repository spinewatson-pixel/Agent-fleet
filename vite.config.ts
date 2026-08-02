import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  root: "src/web",
  publicDir: path.resolve(__dirname, "public"),
  resolve: {
    alias: {
      "@core": path.resolve(__dirname, "src/core"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8787",
    },
  },
  build: {
    outDir: path.resolve(__dirname, "dist/web"),
    emptyOutDir: true,
  },
});
