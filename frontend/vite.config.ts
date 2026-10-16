import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@contract": path.resolve(__dirname, "../docs/contract") } },
  server: { fs: { allow: [path.resolve(__dirname, ".."), __dirname] } },
});
