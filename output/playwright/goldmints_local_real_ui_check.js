const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const baseUrl = "http://127.0.0.1:8811";
const db = "GoldMints_Uat_Manu";
const bnId = 245;
const bnName = "BN/2026/06/0246";
const vendorBnAction = 1651;
const poStatusAction = 1410;
const pickingId = 16793;
const outDir = path.resolve("output/playwright/goldmints_local_real_ui_check");

async function screenshot(page, name) {
  const file = path.join(outDir, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

async function textVisible(page, text, timeout = 15000) {
  await page.getByText(text, { exact: false }).first().waitFor({ state: "visible", timeout });
}

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const results = [];
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

  page.on("pageerror", error => {
    results.push({ step: "pageerror", status: "fail", detail: error.message });
  });

  try {
    await page.goto(`${baseUrl}/web/login?db=${db}`, { waitUntil: "domcontentloaded" });
    await page.locator("input[name='login']").fill("admin");
    await page.locator("input[name='password']").fill("admin");
    await page.locator("button[type='submit']").click();
    await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
    await page.locator(".o_web_client, nav.o_main_navbar").first().waitFor({ timeout: 30000 });
    results.push({ step: "login", status: "pass" });

    await page.goto(`${baseUrl}/web#id=${bnId}&model=vendor.billing.note&view_type=form&action=${vendorBnAction}`, { waitUntil: "domcontentloaded" });
    await textVisible(page, bnName, 30000);
    await screenshot(page, "01_bn_form");
    results.push({ step: "open_bn_form", status: "pass", detail: bnName });

    await page.getByRole("button", { name: /Register Payment|ลงทะเบียนการชำระ|ชำระเงิน/i }).first().click();
    await textVisible(page, "Register Payment", 30000);
    await screenshot(page, "02_register_payment_modal");
    const modalText = await page.locator(".modal, .o_dialog").last().innerText();
    const hasPaymentDifference = /Payment Difference/i.test(modalText);
    const hasBadDifference = /Payment Difference[\s\S]{0,80}[1-9][0-9,]*\.\d{2}/i.test(modalText);
    const hasAmount86 = /86\.00|86\.0|86 ฿|86\.00 ฿/.test(modalText);
    results.push({
      step: "bn_register_payment_modal",
      status: !hasBadDifference && hasAmount86 ? "pass" : "fail",
      detail: { hasPaymentDifference, hasBadDifference, hasAmount86, modalText },
    });

    await page.keyboard.press("Escape");
    await page.waitForTimeout(1000);

    await page.goto(`${baseUrl}/web#action=${poStatusAction}&model=purchase.order.status.report.wizard&view_type=form`, { waitUntil: "domcontentloaded" });
    await textVisible(page, "Purchase Order Status", 30000).catch(async () => {
      await textVisible(page, "Preview", 30000);
    });
    await screenshot(page, "03_po_status_wizard_initial");
    const previewButton = page.getByRole("button", { name: /Preview|แสดงตัวอย่าง/i }).first();
    if (await previewButton.count()) {
      await previewButton.click();
      await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
      await page.waitForTimeout(3000);
    }
    await screenshot(page, "04_po_status_wizard_after_preview");
    const createButtonVisible = await page.getByRole("button", { name: /Create Billing Note/i }).first().isVisible().catch(() => false);
    const lineTabVisible = await page.getByRole("tab", { name: /^Lines$/i }).first().isVisible().catch(() => false);
    const oldPoTabVisible = await page.getByRole("tab", { name: /PO \/ Service Lines/i }).first().isVisible().catch(() => false);
    const oldBillTabVisible = await page.getByRole("tab", { name: /Vendor Bills & Credit Notes/i }).first().isVisible().catch(() => false);
    results.push({
      step: "po_status_wizard_layout",
      status: createButtonVisible && lineTabVisible && !oldPoTabVisible && !oldBillTabVisible ? "pass" : "fail",
      detail: { createButtonVisible, lineTabVisible, oldPoTabVisible, oldBillTabVisible },
    });

    const reportResponse = await page.goto(`${baseUrl}/report/html/stock.report_picking/${pickingId}`, { waitUntil: "domcontentloaded" });
    await screenshot(page, "05_stock_report_picking_html");
    const reportText = await page.locator("body").innerText();
    results.push({
      step: "stock_report_picking_html",
      status: reportResponse && reportResponse.status() === 200 && reportText.includes("UI-MANUAL-MERGE") ? "pass" : "fail",
      detail: { status: reportResponse && reportResponse.status(), containsPicking: reportText.includes("UI-MANUAL-MERGE") },
    });
  } catch (error) {
    results.push({ step: "script", status: "fail", detail: error.message });
    await screenshot(page, "error").catch(() => {});
  } finally {
    await browser.close();
    fs.writeFileSync(path.join(outDir, "results.json"), JSON.stringify(results, null, 2));
    console.log(JSON.stringify(results, null, 2));
    const failed = results.some(result => result.status === "fail");
    process.exit(failed ? 1 : 0);
  }
})();
