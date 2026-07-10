import { expect, test } from "@playwright/test";

// Requires a seeded admin; export E2E_EMAIL / E2E_PASSWORD before running:
//   npm run seed:admin -- e2e@test.local "senha-e2e-123"
//   $env:E2E_EMAIL="e2e@test.local"; $env:E2E_PASSWORD="senha-e2e-123"; npm run e2e
const EMAIL = process.env.E2E_EMAIL ?? "e2e@test.local";
const PASSWORD = process.env.E2E_PASSWORD ?? "senha-e2e-123";

test("unauthenticated access redirects to login", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByText("Acesso restrito")).toBeVisible();
});

test("wrong password shows error and stays out", async ({ page }) => {
  await page.goto("/login");
  await page.fill("#email", EMAIL);
  await page.fill("#password", "senha-errada-999");
  await page.click("button[type=submit]");
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page).toHaveURL(/\/login/);
});

test("valid login reaches overview, /deals paginates", async ({ page }) => {
  await page.goto("/login");
  await page.fill("#email", EMAIL);
  await page.fill("#password", PASSWORD);
  await page.click("button[type=submit]");
  await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });
  await expect(page.getByText("Ofertas (7 dias)")).toBeVisible();

  await page.goto("/deals");
  await expect(page.getByText(/ofertas · página/)).toBeVisible();

  const next = page.getByRole("button", { name: "Próxima" });
  if (await next.isEnabled()) {
    await next.click();
    await expect(page).toHaveURL(/page=2/);
  }
});
