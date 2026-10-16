import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Separate from vite.config.ts (build config) so `vitest` picks up the same
// @contract alias without pulling test-only config into the production build.
const dirname = import.meta.dirname;

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@contract": path.resolve(dirname, "../docs/contract") } },
  test: { environment: "jsdom" },
});
