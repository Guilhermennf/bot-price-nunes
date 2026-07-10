import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname) },
  },
  test: {
    environment: "jsdom",
    include: ["__tests__/**/*.test.tsx", "__tests__/**/*.test.ts"],
    setupFiles: ["__tests__/setup.ts"],
    globals: true,
  },
});
