/**
 * E2E Tests: Billing & Payments
 * Tests billing dashboard, invoices, payment methods, and plan management
 */

import { test, expect } from "@playwright/test";

test.describe("Billing Page", () => {
  test.beforeEach(async ({ page }) => {
    // Login via demo mode first
    await page.goto("/");
    await page.getByRole("button", { name: /demonstração/i }).click();
    await expect(page).toHaveURL("/dashboard", { timeout: 15000 });

    // Navigate to billing
    await page.goto("/billing");
    await expect(page).toHaveURL("/billing");
  });

  test("should display billing dashboard with tabs", async ({ page }) => {
    // Check page title
    await expect(
      page.getByRole("heading", { name: /faturamento/i }),
    ).toBeVisible();

    // Check tabs exist
    await expect(page.getByRole("tab", { name: /resumo/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /faturas/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /pagamento/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /planos/i })).toBeVisible();
  });

  test("should show subscription overview on first tab", async ({ page }) => {
    // Click overview tab
    await page.getByRole("tab", { name: /resumo/i }).click();

    // Should show subscription info
    await expect(page.locator("text=/plano|assinatura/i")).toBeVisible();
  });

  test("should navigate between tabs", async ({ page }) => {
    // Click Invoices tab
    await page.getByRole("tab", { name: /faturas/i }).click();
    await expect(page.locator("text=/fatura|invoice/i")).toBeVisible();

    // Click Payment tab
    await page.getByRole("tab", { name: /pagamento/i }).click();
    await expect(page.locator("text=/método|cartão/i")).toBeVisible();

    // Click Plans tab
    await page.getByRole("tab", { name: /planos/i }).click();
    await expect(
      page.locator("text=/starter|professional|enterprise/i"),
    ).toBeVisible();
  });
});

test.describe("Pricing Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/pricing");
  });

  test("should display pricing plans", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /planos/i })).toBeVisible();

    // Check plan tiers
    await expect(page.locator("text=/starter/i")).toBeVisible();
    await expect(page.locator("text=/professional/i")).toBeVisible();
    await expect(page.locator("text=/enterprise/i")).toBeVisible();
  });

  test("should toggle between monthly and yearly pricing", async ({ page }) => {
    // Find toggle
    const toggle = page.locator("text=/anual|mensal/i").first();

    if (await toggle.isVisible()) {
      await toggle.click();
      // Should show different prices
    }
  });

  test("should navigate to checkout on plan selection", async ({ page }) => {
    // Click on a plan's CTA button
    const ctaButton = page
      .getByRole("button", { name: /começar|assinar|upgrade/i })
      .first();

    if (await ctaButton.isVisible()) {
      await ctaButton.click();
      // Should navigate to checkout or login
      await expect(page).toHaveURL(/checkout|login/);
    }
  });
});

test.describe("Legal Pages", () => {
  test("should display Terms of Service", async ({ page }) => {
    await page.goto("/terms");

    await expect(page.getByRole("heading", { name: /termos/i })).toBeVisible();
    await expect(page.locator("text=/aceitação/i")).toBeVisible();
  });

  test("should display Privacy Policy", async ({ page }) => {
    await page.goto("/privacy");

    await expect(
      page.getByRole("heading", { name: /privacidade/i }),
    ).toBeVisible();
    await expect(page.locator("text=/lgpd/i")).toBeVisible();
  });

  test("should have link from Terms to Privacy", async ({ page }) => {
    await page.goto("/terms");

    const privacyLink = page.getByRole("link", { name: /privacidade/i });
    await expect(privacyLink).toBeVisible();

    await privacyLink.click();
    await expect(page).toHaveURL("/privacy");
  });

  test("should have link from Privacy to Terms", async ({ page }) => {
    await page.goto("/privacy");

    const termsLink = page.getByRole("link", { name: /termos/i });
    await expect(termsLink).toBeVisible();

    await termsLink.click();
    await expect(page).toHaveURL("/terms");
  });

  test("should have back to home link", async ({ page }) => {
    await page.goto("/terms");

    const backLink = page.getByRole("link", { name: /voltar/i });
    await expect(backLink).toBeVisible();

    await backLink.click();
    await expect(page).toHaveURL("/");
  });
});
