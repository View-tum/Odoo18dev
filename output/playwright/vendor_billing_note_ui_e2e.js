const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const baseUrl = "http://127.0.0.1:8811";
const db = "GoldMints_Uat_Manu";
const wizardId = process.env.UI_E2E_WIZARD_ID || "56";
const poActionId = "1410";
const billingActionId = "1651";
const outDir = path.join(process.cwd(), "output", "playwright");

function fail(message, details) {
  const err = new Error(message);
  err.details = details;
  throw err;
}

async function waitForOdoo(page) {
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(1200);
}

async function checkNoUiError(page, label) {
  const errorSelectors = [
    ".o_error_dialog",
    ".modal:has-text('RPC_ERROR')",
    ".o_notification:has-text('RPC_ERROR')",
    "text=Odoo Server Error",
    "text=RPC_ERROR",
  ];
  for (const selector of errorSelectors) {
    if (await page.locator(selector).count()) {
      await page.screenshot({ path: path.join(outDir, `${label}-error.png`), fullPage: true });
      fail(`UI error detected at ${label}: ${selector}`);
    }
  }
}

async function clickButton(page, name) {
  const button = page.getByRole("button", { name });
  await button.first().waitFor({ state: "visible", timeout: 30000 });
  await button.first().click();
  await waitForOdoo(page);
}

(async () => {
  fs.mkdirSync(outDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  const rpcErrors = [];

  page.on("response", (response) => {
    const url = response.url();
    if (
      response.status() >= 400 &&
      /\/web\/(dataset|action|session|webclient|login)/.test(url)
    ) {
      rpcErrors.push(`${response.status()} ${url}`);
    }
  });
  page.on("pageerror", (error) => rpcErrors.push(`PAGEERROR ${error.message}`));

  await page.goto(`${baseUrl}/web/login?db=${encodeURIComponent(db)}`, { waitUntil: "domcontentloaded" });
  await page.locator("input[name='login']").fill("admin");
  await page.locator("input[name='password']").fill("admin");
  await page.locator("button[type='submit']").click();
  await page.waitForURL(/\/(web|odoo)/, { timeout: 60000 });
  await waitForOdoo(page);
  await checkNoUiError(page, "login");

  await page.goto(`${baseUrl}/web#id=145&model=vendor.billing.note&view_type=form&action=${billingActionId}`, { waitUntil: "domcontentloaded" });
  await waitForOdoo(page);
  await page.getByText("BN/2026/06/0145").first().waitFor({ state: "visible", timeout: 30000 });
  await page.screenshot({ path: path.join(outDir, "bn-0145-mixed-paid.png"), fullPage: true });
  await checkNoUiError(page, "open-existing-mixed-bn");

  await page.goto(`${baseUrl}/web#id=${wizardId}&model=purchase.order.status.report.wizard&view_type=form&action=${poActionId}`, { waitUntil: "domcontentloaded" });
  await waitForOdoo(page);
  await page.getByText("APD/2026/06/0010").first().waitFor({ state: "visible", timeout: 30000 });
  await page.getByText("RAPD/2026/06/0007").first().waitFor({ state: "visible", timeout: 30000 });
  if (await page.getByText("Vendor Bills & Credit Notes", { exact: true }).count()) {
    fail("Old separate Vendor Bills & Credit Notes tab is still visible");
  }
  await page.screenshot({ path: path.join(outDir, "po-status-wizard-apd-cn-lines.png"), fullPage: true });
  await checkNoUiError(page, "open-po-status-wizard");

  await clickButton(page, "Select APD/CN");
  await checkNoUiError(page, "select-bills-credit-notes");
  await clickButton(page, "Create Billing Note");
  await page.locator(".o_form_view").waitFor({ state: "visible", timeout: 30000 });
  await page.getByText("UI-E2E-BN-20260605-0805-BILL").first().waitFor({ state: "visible", timeout: 30000 });
  await page.screenshot({ path: path.join(outDir, "created-bn-from-po-status.png"), fullPage: true });
  await checkNoUiError(page, "create-billing-note");

  await clickButton(page, "Confirm");
  await checkNoUiError(page, "confirm-billing-note");
  await clickButton(page, "Register Payment");
  await page.getByRole("dialog").waitFor({ state: "visible", timeout: 30000 });
  await page.getByText("Register Payment").first().waitFor({ state: "visible", timeout: 30000 });
  await page.screenshot({ path: path.join(outDir, "register-payment-net-750.png"), fullPage: true });
  await checkNoUiError(page, "register-payment-dialog");

  const dialogText = await page.getByRole("dialog").innerText();
  if (!/750\.00|750,00/.test(dialogText)) {
    fail("Register Payment dialog does not show net amount 750.00", dialogText);
  }
  const diffMatch = dialogText.replace(/\u00a0/g, " ").match(/Payment Difference\s+(-?[\d,]+\.\d{2})/i);
  if (diffMatch) {
    const diff = Number(diffMatch[1].replace(/,/g, ""));
    if (Math.abs(diff) > 0.0001) {
      fail(`Payment Difference is non-zero: ${diffMatch[1]}`, dialogText);
    }
  }
  if (rpcErrors.length) {
    fail("RPC/page errors were captured", rpcErrors.join("\n"));
  }

  console.log("UI_E2E_PASS");
  console.log(`WIZARD_ID ${wizardId}`);
  console.log("CHECKED_EXISTING_BN BN/2026/06/0145");
  console.log("CHECKED_MOVES APD/2026/06/0010 RAPD/2026/06/0007");
  console.log("SCREENSHOTS output/playwright/bn-0145-mixed-paid.png output/playwright/po-status-wizard-apd-cn-lines.png output/playwright/created-bn-from-po-status.png output/playwright/register-payment-net-750.png");

  await browser.close();
})().catch(async (error) => {
  console.error("UI_E2E_FAIL", error.message);
  if (error.details) {
    console.error(String(error.details).slice(0, 4000));
  }
  process.exit(1);
});
