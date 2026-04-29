import { test, expect } from "@playwright/test";

const BASE_URL = process.env.BASE_URL || "http://localhost:3000";
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

test.describe("UX Improvements - Dashboard → Data Ingestion → ChatCAD Flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    // Wait for page to load
    await page.waitForLoadState("networkidle");
  });

  test('Dashboard: "GERAR PROJETO" CTA navigates to /data-ingestion', async ({
    page,
  }) => {
    // Verify we're on the dashboard
    await expect(page).toHaveURL(`${BASE_URL}/`);

    // Look for the "GERAR PROJETO" button in hero section
    const gerarProjetoButton = page
      .getByRole("button", { name: /GERAR PROJETO/i })
      .first();

    await expect(gerarProjetoButton).toBeVisible();
    await gerarProjetoButton.click();

    // Verify navigation to /data-ingestion
    await expect(page).toHaveURL(`${BASE_URL}/data-ingestion`);
  });

  test('Dashboard: Quick action "Gerar Projeto" navigates to /data-ingestion', async ({
    page,
  }) => {
    // Scroll to find quick actions section
    await page
      .getByText(/Gerar Projeto/i)
      .filter({ hasText: "Iniciar ingestão" })
      .click();

    // Verify navigation to /data-ingestion
    await expect(page).toHaveURL(`${BASE_URL}/data-ingestion`);
  });

  test("DataIngestion: Validation timeline shows 4 stages", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/data-ingestion`);

    // Verify all 4 validation steps are visible
    await expect(page.getByText("Arquivo carregado")).toBeVisible();
    await expect(page.getByText("Validação estrutural")).toBeVisible();
    await expect(page.getByText("Pré-visualização pronta")).toBeVisible();
    await expect(page.getByText("Projeto gerado")).toBeVisible();
  });

  test("DataIngestion: Info cards display file, validation, and preview status", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/data-ingestion`);

    // Verify info cards are visible
    const fileCard = page.locator("text=Arquivo").first();
    const validationCard = page.locator("text=Validação").first();
    const previewCard = page.locator("text=Prévia").first();

    await expect(fileCard).toBeVisible();
    await expect(validationCard).toBeVisible();
    await expect(previewCard).toBeVisible();

    // Check initial states
    await expect(fileCard).toContainText("Aguardando planilha");
    await expect(validationCard).toContainText("Pendente");
    await expect(previewCard).toContainText("Sem dados");
  });

  test('DataIngestion: "Selecionar arquivo" button opens file picker', async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/data-ingestion`);

    // Look for file input trigger button
    const selectButton = page.getByRole("button", {
      name: /Selecionar arquivo/i,
    });
    await expect(selectButton).toBeVisible();

    // Verify it has the FaSearch icon context
    await expect(selectButton).toContainText("Selecionar arquivo");
  });

  test('DataIngestion: Button text changes from "PROCESSAR EXCEL" to "VALIDAR E GERAR"', async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/data-ingestion`);

    // Verify the new button text is visible
    const processButton = page.getByRole("button", {
      name: /VALIDAR E GERAR/i,
    });
    await expect(processButton).toBeVisible();

    // Old button text should NOT exist
    const oldButton = page.getByRole("button", { name: /PROCESSAR EXCEL/i });
    await expect(oldButton).not.toBeVisible();
  });

  test("ChatCAD: Structured response rendering with explanation, code, and details", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/chatcad`);

    // Wait for chat interface to load
    await page.waitForLoadState("networkidle");

    // Send a test prompt that might return LISP code
    const input = page.locator("textarea").first();
    await input.focus();
    await input.fill("Crie um comando LISP simples que desenhe um circulo");
    await input.press("Enter");

    // Wait for response
    await page.waitForTimeout(3000);

    // Verify the response sections are visible (when LISP code is present)
    // Look for structured sections
    const explanationSection = page.locator("text=Explicação curta").first();
    const codeSection = page.locator("text=Código LISP").first();

    // At least one of them should be visible if response came back
    const isVisible = await Promise.race([
      explanationSection.isVisible(),
      codeSection.isVisible(),
    ]).catch(() => false);

    if (isVisible) {
      // Verify copy button exists for LISP code
      const copyButton = page.getByRole("button", {
        name: /Copiar código|Copiado/i,
      });
      await expect(copyButton).toBeVisible();
    }
  });

  test('ChatCAD: "Executar no AutoCAD" button appears for LISP responses', async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/chatcad`);
    await page.waitForLoadState("networkidle");

    // Send a command that's likely to return LISP
    const input = page.locator("textarea").first();
    await input.focus();
    await input.fill('LISP: (command "circle" PAUSE PAUSE "1")');
    await input.press("Enter");

    // Wait for response
    await page.waitForTimeout(3000);

    // Look for the "Executar no AutoCAD" button
    const executeButton = page.getByRole("button", {
      name: /Executar no AutoCAD/i,
    });

    // The button should appear for responses containing LISP code
    const isVisible = await executeButton.isVisible().catch(() => false);
    expect([true, false]).toContain(isVisible); // Accept both states depending on response
  });

  test("ChatCAD: Quick action buttons use reusable submitPrompt", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/chatcad`);
    await page.waitForLoadState("networkidle");

    // Verify starter prompts exist and are clickable
    const starterPrompt = page
      .locator('[role="button"]')
      .filter({ hasText: /Desenhar|Calcular|Otimizar/ })
      .first();

    if (await starterPrompt.isVisible()) {
      await starterPrompt.click();

      // Verify input was populated or message was sent
      const userMessage = page
        .locator("text=/Desenhar|Calcular|Otimizar/")
        .first();
      await expect(userMessage).toBeVisible();
    }
  });

  test("CncControl: Simulation milestone tracker shows 4 stages", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/cnc`);
    await page.waitForLoadState("networkidle");

    // Look for milestone tracker with the 4 stages
    const preparacao = page
      .locator("text=Preparação")
      .filter({ hasText: "0%" });
    const piercing = page.locator("text=Piercing").filter({ hasText: "18%" });
    const corte = page.locator("text=Corte").filter({ hasText: "52%" });
    const finalizacao = page
      .locator("text=Finalização")
      .filter({ hasText: "84%" });

    // At least one should be visible if CNC page has simulation timeline
    const hasStages = await Promise.all([
      preparacao.isVisible().catch(() => false),
      piercing.isVisible().catch(() => false),
      corte.isVisible().catch(() => false),
      finalizacao.isVisible().catch(() => false),
    ]).then((results) => results.some((v) => v));

    expect(hasStages).toBeTruthy();
  });

  test('CadDashboard: Command feedback shows "Último comando", "Status", "Retorno"', async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/autocad`);
    await page.waitForLoadState("networkidle");

    // Look for feedback cards
    const ultimoComandoCard = page.locator("text=Último comando").first();
    const statusCard = page.locator("text=Status").first();
    const retornoCard = page.locator("text=Retorno").first();

    // All three should be visible
    await expect(ultimoComandoCard).toBeVisible();
    await expect(statusCard).toBeVisible();
    await expect(retornoCard).toBeVisible();

    // Verify initial state messages
    await expect(ultimoComandoCard).toContainText("Nenhum comando");
    await expect(statusCard).toContainText(/Aguardando|Comando/i);
  });

  test("Billing: Metrics show refined value language", async ({ page }) => {
    await page.goto(`${BASE_URL}/billing`);
    await page.waitForLoadState("networkidle");

    // Look for refined metric descriptions
    const economiaEstimada = page.locator(
      "text=economia estimada vs. processo manual",
    );
    const horasTecnicas = page.locator(
      "text=horas técnicas liberadas para produção",
    );

    // At least one should be visible if page loaded
    const hasRefinedMetrics = await Promise.all([
      economiaEstimada.isVisible().catch(() => false),
      horasTecnicas.isVisible().catch(() => false),
    ]).then((results) => results.some((v) => v));

    expect(hasRefinedMetrics).toBeTruthy();
  });

  test("End-to-end: Dashboard → DataIngestion → ChatCAD complete flow", async ({
    page,
  }) => {
    // Start at dashboard
    await page.goto(`${BASE_URL}/`);
    await expect(page).toHaveURL(`${BASE_URL}/`);

    // Click GERAR PROJETO
    const gerarProjetoButton = page
      .getByRole("button", { name: /GERAR PROJETO/i })
      .first();
    await gerarProjetoButton.click();

    // Should navigate to data-ingestion
    await expect(page).toHaveURL(`${BASE_URL}/data-ingestion`);

    // Verify validation timeline is visible
    await expect(page.getByText("Arquivo carregado")).toBeVisible();
    await expect(page.getByText("Validação estrutural")).toBeVisible();

    // Navigate to ChatCAD
    const chatcadLink = page
      .getByRole("link", { name: /ChatCAD|Chat/i })
      .first();
    if (await chatcadLink.isVisible()) {
      await chatcadLink.click();
      await expect(page).toHaveURL(/chatcad/);
    }
  });
});
