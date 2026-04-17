/**
 * E2E Tests: Authentication Flow
 * Tests login, register, password recovery, and demo mode
 */

import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("should display login page correctly", async ({ page }) => {
    // Check branding
    await expect(page.locator("text=ENGENHARIA")).toBeVisible();
    await expect(page.locator("text=CAD")).toBeVisible();

    // Check form elements
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.getByRole("button", { name: /entrar/i })).toBeVisible();
  });

  test("should toggle between login and register modes", async ({ page }) => {
    // Initially should be in login mode
    await expect(page.getByRole("button", { name: /entrar/i })).toBeVisible();

    // Click to switch to register
    await page.getByText(/criar conta/i).click();

    // Should show register button
    await expect(
      page.getByRole("button", { name: /criar conta/i }),
    ).toBeVisible();
  });

  test("should show validation error for empty fields", async ({ page }) => {
    const submitButton = page.getByRole("button", { name: /entrar/i });
    await submitButton.click();

    // Form should not submit (HTML5 validation)
    await expect(page).toHaveURL("/");
  });

  test("should show error for invalid credentials", async ({ page }) => {
    await page.fill('input[type="email"]', "invalid@test.com");
    await page.fill('input[type="password"]', "wrongpassword");
    await page.getByRole("button", { name: /entrar/i }).click();

    // Should show error message
    await expect(page.locator("text=/erro|inválid|incorret/i")).toBeVisible({
      timeout: 10000,
    });
  });

  test("should allow demo login", async ({ page }) => {
    const demoButton = page.getByRole("button", { name: /demonstração/i });
    await expect(demoButton).toBeVisible();

    await demoButton.click();

    // Should redirect to dashboard
    await expect(page).toHaveURL("/dashboard", { timeout: 15000 });
  });

  test("should navigate to forgot password", async ({ page }) => {
    await page.getByText(/esquec/i).click();
    await expect(page).toHaveURL("/forgot-password");
  });

  test("should navigate to pricing page", async ({ page }) => {
    await page.getByRole("button", { name: /planos/i }).click();
    await expect(page).toHaveURL("/pricing");
  });
});

test.describe("Password Recovery", () => {
  test("should display forgot password form", async ({ page }) => {
    await page.goto("/forgot-password");

    await expect(page.getByRole("heading", { name: /senha/i })).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeVisible();
  });

  test("should validate email format", async ({ page }) => {
    await page.goto("/forgot-password");

    await page.fill('input[type="email"]', "invalid-email");
    await page.getByRole("button", { name: /enviar|recuperar/i }).click();

    // Should not navigate away due to HTML5 validation
    await expect(page).toHaveURL("/forgot-password");
  });
});
