import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vite.dev/config/
const dirname = import.meta.dirname;

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@contract": path.resolve(dirname, "../docs/contract") } },
  server: { fs: { allow: [path.resolve(dirname, ".."), dirname] } },
});
