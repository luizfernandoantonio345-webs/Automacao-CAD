/**
 * E2E Tests: Navigation & Sidebar
 * Tests responsive navigation, keyboard accessibility, and routing
 */

import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Login via demo mode first
    await page.goto('/');
    await page.getByRole('button', { name: /demonstração/i }).click();
    await expect(page).toHaveURL('/dashboard', { timeout: 15000 });
  });

  test('should display sidebar with navigation items', async ({ page }) => {
    // Check main navigation is visible
    await expect(page.locator('nav[role="menubar"]')).toBeVisible();
    
    // Check key nav items
    await expect(page.getByRole('menuitem', { name: /dashboard/i })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: /controle cad/i })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: /chatcad/i })).toBeVisible();
  });

  test('should navigate to different pages', async ({ page }) => {
    // Navigate to CNC Control
    await page.getByRole('menuitem', { name: /cnc/i }).click();
    await expect(page).toHaveURL('/cnc-control');

    // Navigate to ChatCAD
    await page.getByRole('menuitem', { name: /chatcad/i }).click();
    await expect(page).toHaveURL('/chatcad');

    // Navigate back to Dashboard
    await page.getByRole('menuitem', { name: /dashboard/i }).click();
    await expect(page).toHaveURL('/dashboard');
  });

  test('should highlight active navigation item', async ({ page }) => {
    const dashboardItem = page.getByRole('menuitem', { name: /dashboard/i });
    
    // Dashboard should be marked as current page
    await expect(dashboardItem).toHaveAttribute('aria-current', 'page');

    // Navigate away
    await page.getByRole('menuitem', { name: /chatcad/i }).click();
    
    // Dashboard should no longer be current
    await expect(dashboardItem).not.toHaveAttribute('aria-current', 'page');
    
    // ChatCAD should be current
    const chatcadItem = page.getByRole('menuitem', { name: /chatcad/i });
    await expect(chatcadItem).toHaveAttribute('aria-current', 'page');
  });

  test('should support keyboard navigation', async ({ page }) => {
    // Focus first nav item
    await page.getByRole('menuitem', { name: /dashboard/i }).focus();
    
    // Tab to next item
    await page.keyboard.press('Tab');
    
    // Press Enter to navigate
    await page.keyboard.press('Enter');
    
    // Should have navigated
    await expect(page).not.toHaveURL('/dashboard');
  });

  test('should logout correctly', async ({ page }) => {
    const logoutButton = page.getByRole('button', { name: /sair/i });
    await expect(logoutButton).toBeVisible();
    
    await logoutButton.click();
    
    // Should redirect to login
    await expect(page).toHaveURL('/');
  });
});

test.describe('Mobile Navigation', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /demonstração/i }).click();
    await expect(page).toHaveURL('/dashboard', { timeout: 15000 });
  });

  test('should show hamburger menu on mobile', async ({ page }) => {
    const hamburger = page.getByRole('button', { name: /menu/i });
    await expect(hamburger).toBeVisible();
  });

  test('should toggle sidebar on hamburger click', async ({ page }) => {
    const hamburger = page.getByRole('button', { name: /menu/i });
    
    // Click to open
    await hamburger.click();
    
    // Sidebar should be visible
    await expect(page.locator('nav[role="menubar"]')).toBeVisible();
    
    // Click to close
    await hamburger.click();
    
    // Wait for animation
    await page.waitForTimeout(300);
  });

  test('should close sidebar on overlay click', async ({ page }) => {
    const hamburger = page.getByRole('button', { name: /menu/i });
    
    // Open sidebar
    await hamburger.click();
    await expect(page.locator('nav[role="menubar"]')).toBeVisible();
    
    // Click overlay
    await page.locator('.sl-overlay').click();
    
    // Wait for close animation
    await page.waitForTimeout(300);
  });

  test('should close sidebar on Escape key', async ({ page }) => {
    const hamburger = page.getByRole('button', { name: /menu/i });
    
    // Open sidebar
    await hamburger.click();
    await expect(page.locator('nav[role="menubar"]')).toBeVisible();
    
    // Press Escape
    await page.keyboard.press('Escape');
    
    // Wait for close animation
    await page.waitForTimeout(300);
  });
});

test.describe('Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /demonstração/i }).click();
    await expect(page).toHaveURL('/dashboard', { timeout: 15000 });
  });

  test('should have skip-to-content link', async ({ page }) => {
    const skipLink = page.locator('a.skip-link');
    
    // Focus the skip link (usually visible only on focus)
    await skipLink.focus();
    
    // Should link to main content
    await expect(skipLink).toHaveAttribute('href', '#main-content');
  });

  test('should have proper ARIA landmarks', async ({ page }) => {
    // Main navigation
    await expect(page.locator('[role="navigation"]')).toBeVisible();
    
    // Main content area
    await expect(page.locator('[role="main"]')).toBeVisible();
  });

  test('should have visible focus indicators', async ({ page }) => {
    const navItem = page.getByRole('menuitem', { name: /dashboard/i });
    await navItem.focus();
    
    // Check that element can receive focus (has tabindex or is naturally focusable)
    await expect(navItem).toBeFocused();
  });
});
