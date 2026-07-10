import { defineConfig } from "@playwright/test";

// e2e runs locally against the dev server with real .env.local credentials
// and a seeded admin (npm run seed:admin). Not part of CI.
export default defineConfig({
  testDir: "./e2e",
  timeout: 45_000,
  use: {
    baseURL: "http://localhost:3100",
    headless: true,
  },
  webServer: {
    command: "npx next dev -p 3100",
    url: "http://localhost:3100/login",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
