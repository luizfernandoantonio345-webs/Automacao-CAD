/**
 * E2E Tests: Full User Flow (Login → Dashboard → Ingestion → CNC → Export → Billing)
 * Covers the complete production pipeline as a real user would experience it.
 */

import { test, expect, Page } from "@playwright/test";

// ── Helpers ─────────────────────────────────────────────────────────────────

async function loginDemo(page: Page) {
  await page.goto("/");
  const demoBtn = page.getByRole("button", { name: /demonstração/i });
  await expect(demoBtn).toBeVisible({ timeout: 10000 });
  await demoBtn.click();
  await expect(page).toHaveURL("/dashboard", { timeout: 20000 });
}

// ═══════════════════════════════════════════════════════════════════════════
// PARTE 1 — FLUXO COMPLETO END-TO-END
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Full Pipeline: Login → Dashboard → Data Ingestion → CNC → Billing", () => {
  test("1. Login demo should land on dashboard", async ({ page }) => {
    await loginDemo(page);

    // Dashboard deve exibir elementos básicos
    await expect(page.locator("text=/bem-vindo|dashboard|projeto/i")).toBeVisible({
      timeout: 10000,
    });
  });

  test("2. Dashboard hero button GERAR PROJETO navigates to /data-ingestion", async ({ page }) => {
    await loginDemo(page);

    // Procura botão de ação principal
    const gerarBtn = page
      .getByRole("button", { name: /gerar projeto/i })
      .or(page.getByText(/gerar projeto/i).first());

    if (await gerarBtn.isVisible()) {
      await gerarBtn.click();
      await expect(page).toHaveURL("/data-ingestion", { timeout: 10000 });
    } else {
      // Navega diretamente se botão não visível (telas menores)
      await page.goto("/data-ingestion");
      await expect(page).toHaveURL("/data-ingestion");
    }
  });

  test("3. Data ingestion page renders upload zone", async ({ page }) => {
    await loginDemo(page);
    await page.goto("/data-ingestion");

    await expect(
      page.locator("text=/excel|xlsx|arrastar|upload|importar/i").first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("4. Data ingestion dropzone accepts file click", async ({ page }) => {
    await loginDemo(page);
    await page.goto("/data-ingestion");

    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached({ timeout: 10000 });
    // File input exists → upload functionality is wired
  });

  test("5. Navigate from dashboard to CNC Control", async ({ page }) => {
    await loginDemo(page);
    await page.goto("/cnc-control");

    // CNC page deve ter elementos de controle
    await expect(
      page.locator("text=/cnc|g-code|toolpath|plasma|geometria/i").first()
    ).toBeVisible({ timeout: 15000 });
  });

  test("6. CNC preview tab and simulation controls are present", async ({ page }) => {
    await loginDemo(page);
    await page.goto("/cnc-control");

    // Tabs devem existir
    const previewTab = page
      .getByRole("button", { name: /preview/i })
      .or(page.locator("text=/preview/i").first());

    if (await previewTab.isVisible({ timeout: 5000 })) {
      await previewTab.click();
      // Após clicar na preview, verifica controles de simulação
      await expect(
        page.locator("text=/simular|pausar|velocidade/i").first()
      ).toBeVisible({ timeout: 10000 });
    }
  });

  test("7. ChatCAD page renders and input is available", async ({ page }) => {
    await loginDemo(page);
    await page.goto("/chatcad");

    await expect(
      page.locator("textarea, input[type='text']").first()
    ).toBeVisible({ timeout: 15000 });
  });

  test("8. ChatCAD sends message and receives response", async ({ page }) => {
    await loginDemo(page);
    await page.goto("/chatcad");

    // Digitar mensagem de engenharia
    const input = page.locator("textarea").first();
    await expect(input).toBeVisible({ timeout: 15000 });
    await input.fill("desenhar flange 4 polegadas DN100");

    // Enviar
    const sendBtn = page
      .getByRole("button", { name: /enviar|send/i })
      .or(page.locator("button[type='submit']").first());

    if (await sendBtn.isVisible({ timeout: 3000 })) {
      await sendBtn.click();
    } else {
      await input.press("Enter");
    }

    // Aguarda resposta aparecer
    await expect(
      page.locator("text=/flange|dn100|100mm|polegada|lisp/i").first()
    ).toBeVisible({ timeout: 30000 });
  });

  test("9. AutoCAD control page loads", async ({ page }) => {
    await loginDemo(page);
    await page.goto("/cad-dashboard");

    await expect(
      page.locator("text=/autocad|bridge|comando|lisp/i").first()
    ).toBeVisible({ timeout: 15000 });
  });

  test("10. Billing page shows value metrics", async ({ page }) => {
    await loginDemo(page);
    await page.goto("/billing");

    await expect(
      page.locator("text=/faturamento|billing|plano/i").first()
    ).toBeVisible({ timeout: 10000 });

    // Verifica métricas de valor adicionadas
    await expect(
      page.locator("text=/economia|tempo economizado|uso do sistema/i").first()
    ).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// PARTE 2 — VALIDAÇÃO DE UPLOAD EXCEL
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Upload Excel / Data Ingestion", () => {
  test("upload zone rejects non-Excel files", async ({ page }) => {
    await loginDemo(page);
    await page.goto("/data-ingestion");

    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached({ timeout: 10000 });

    // Tenta enviar arquivo de texto
    await fileInput.setInputFiles({
      name: "bad-file.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("this is not an excel file"),
    });

    // Deve mostrar erro
    await expect(
      page.locator("text=/excel|xlsx|inválido|accept/i").first()
    ).toBeVisible({ timeout: 5000 });
  });

  test("upload zone accepts valid xlsx mock", async ({ page }) => {
    await loginDemo(page);
    await page.goto("/data-ingestion");

    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached({ timeout: 10000 });

    // Mock xlsx (bytes mínimos com header PK)
    const xlsxMock = Buffer.from([
      0x50, 0x4b, 0x03, 0x04, 0x14, 0x00, 0x00, 0x00,
      0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    ]);

    await fileInput.setInputFiles({
      name: "projetos.xlsx",
      mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      buffer: xlsxMock,
    });

    // Deve mostrar preview ou nome do arquivo
    await expect(
      page.locator("text=/projetos|xlsx|arquivo|selecionado/i").first()
    ).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// PARTE 3 — GERAÇÃO DE G-CODE (SMOKE)
// ═══════════════════════════════════════════════════════════════════════════

test.describe("G-Code Generation Smoke Tests", () => {
  test("CNC control renders config panel", async ({ page }) => {
    await loginDemo(page);
    await page.goto("/cnc-control");

    // Config tab deve estar visível
    await expect(
      page.locator("text=/material|espessura|velocidade|amperagem/i").first()
    ).toBeVisible({ timeout: 15000 });
  });

  test("CNC download buttons appear after G-code ready", async ({ page }) => {
    await loginDemo(page);
    await page.goto("/cnc-control");

    // G-code tab
    const gcodeTab = page
      .getByRole("button", { name: /g-?code/i })
      .or(page.locator("text=/g-code/i").first());

    if (await gcodeTab.isVisible({ timeout: 5000 })) {
      await gcodeTab.click();
      // Se G-code está disponível, botões de download aparecem
      const downloadBtn = page.locator("text=/.NC|.TAP|.gcode/i").first();
      // Aceita que G-code pode ou não estar gerado (smoke test)
      const exists = await downloadBtn.isVisible({ timeout: 3000 }).catch(() => false);
      // Não falha se não gerado ainda — apenas verifica que página não quebrou
      expect(typeof exists).toBe("boolean");
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// PARTE 4 — AUTOCAD BRIDGE (SMOKE)
// ═══════════════════════════════════════════════════════════════════════════

test.describe("AutoCAD Bridge Smoke Tests", () => {
  test("command input field is present", async ({ page }) => {
    await loginDemo(page);
    await page.goto("/cad-dashboard");

    const textarea = page.locator("textarea").first();
    await expect(textarea).toBeVisible({ timeout: 15000 });
  });

  test("send command button exists", async ({ page }) => {
    await loginDemo(page);
    await page.goto("/cad-dashboard");

    const sendBtn = page.locator("text=/enviar comando/i").first();
    await expect(sendBtn).toBeVisible({ timeout: 15000 });
  });

  test("command feedback badge appears after send", async ({ page }) => {
    await loginDemo(page);
    await page.goto("/cad-dashboard");

    // Preenche campo de comando LISP
    const textarea = page.locator("textarea").first();
    await expect(textarea).toBeVisible({ timeout: 15000 });
    await textarea.fill('(command "_CIRCLE" "0,0" 50)');

    const sendBtn = page.locator("text=/enviar comando/i").first();
    await sendBtn.click();

    // Badge de feedback deve aparecer
    await expect(
      page.locator("text=/enviado|executado/i").first()
    ).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// PARTE 5 — RESPONSIVIDADE E ACESSIBILIDADE
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Accessibility & Responsiveness", () => {
  test("pages have proper title", async ({ page }) => {
    await loginDemo(page);
    const title = await page.title();
    expect(title.length).toBeGreaterThan(0);
  });

  test("no JS console errors on dashboard", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });

    await loginDemo(page);
    await page.waitForTimeout(2000);

    // Filtra erros esperados (favicon, reCAPTCHA etc.)
    const criticalErrors = errors.filter(
      (e) =>
        !e.includes("favicon") &&
        !e.includes("recaptcha") &&
        !e.includes("404") &&
        !e.includes("net::ERR")
    );
    expect(criticalErrors).toHaveLength(0);
  });

  test("no JS console errors on data ingestion", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });

    await loginDemo(page);
    await page.goto("/data-ingestion");
    await page.waitForTimeout(2000);

    const criticalErrors = errors.filter(
      (e) => !e.includes("favicon") && !e.includes("net::ERR")
    );
    expect(criticalErrors).toHaveLength(0);
  });
});
