const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const baseUrl = "http://127.0.0.1:8811";
const db = "GoldMints_Uat_Manu";
const billingNoteId = process.env.UI_E2E_BN_ID || "166";
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
  await checkNoUiError(page, "payment-login");

  await page.goto(`${baseUrl}/web#id=${billingNoteId}&model=vendor.billing.note&view_type=form&action=${billingActionId}`, { waitUntil: "domcontentloaded" });
  await waitForOdoo(page);
  await page.getByText("BN/2026/06/0166").first().waitFor({ state: "visible", timeout: 30000 });
  await checkNoUiError(page, "payment-open-bn");

  await clickButton(page, "Register Payment");
  await page.getByRole("dialog").waitFor({ state: "visible", timeout: 30000 });
  await page.screenshot({ path: path.join(outDir, "register-payment-default-ap-journal.png"), fullPage: true });
  await checkNoUiError(page, "payment-dialog");

  const dialogText = await page.getByRole("dialog").innerText();
  if (!/750\.00|750,00/.test(dialogText)) {
    fail("Register Payment dialog does not show amount 750.00", dialogText);
  }
  if (/Cheque for Customer Invoices/i.test(dialogText)) {
    fail("Register Payment still defaults to customer cheque journal", dialogText);
  }
  const diffMatch = dialogText.replace(/\u00a0/g, " ").match(/Payment Difference\s+(-?[\d,]+\.\d{2})/i);
  if (diffMatch) {
    const diff = Number(diffMatch[1].replace(/,/g, ""));
    if (Math.abs(diff) > 0.0001) {
      fail(`Payment Difference is non-zero: ${diffMatch[1]}`, dialogText);
    }
  }

  await clickButton(page, "Create Payment");
  await page.getByRole("dialog").waitFor({ state: "hidden", timeout: 60000 }).catch(() => {});
  await waitForOdoo(page);
  await checkNoUiError(page, "payment-created");
  await page.screenshot({ path: path.join(outDir, "bn-0166-paid-after-ui-payment.png"), fullPage: true });

  if (rpcErrors.length) {
    fail("RPC/page errors were captured", rpcErrors.join("\n"));
  }

  console.log("UI_PAYMENT_E2E_PASS");
  console.log("CHECKED_BN BN/2026/06/0166");
  console.log("SCREENSHOTS output/playwright/register-payment-default-ap-journal.png output/playwright/bn-0166-paid-after-ui-payment.png");

  await browser.close();
})().catch((error) => {
  console.error("UI_PAYMENT_E2E_FAIL", error.message);
  if (error.details) {
    console.error(String(error.details).slice(0, 4000));
  }
  process.exit(1);
});
