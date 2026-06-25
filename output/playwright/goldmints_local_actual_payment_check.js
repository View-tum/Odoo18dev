const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const baseUrl = "http://127.0.0.1:8811";
const db = "GoldMints_Uat_Manu";
const bnId = 246;
const bnName = "BN/2026/06/0247";
const vendorBnAction = 1651;
const outDir = path.resolve("output/playwright/goldmints_local_actual_payment_check");

async function screenshot(page, name) {
  const file = path.join(outDir, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const results = [];
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

  try {
    await page.goto(`${baseUrl}/web/login?db=${db}`, { waitUntil: "domcontentloaded" });
    await page.locator("input[name='login']").fill("admin");
    await page.locator("input[name='password']").fill("admin");
    await page.locator("button[type='submit']").click();
    await page.locator(".o_web_client, nav.o_main_navbar").first().waitFor({ timeout: 30000 });
    results.push({ step: "login", status: "pass" });

    await page.goto(`${baseUrl}/web#id=${bnId}&model=vendor.billing.note&view_type=form&action=${vendorBnAction}`, { waitUntil: "domcontentloaded" });
    await page.getByText(bnName, { exact: false }).first().waitFor({ state: "visible", timeout: 30000 });
    await screenshot(page, "01_bn_before_payment");
    results.push({ step: "open_bn", status: "pass" });

    await page.getByRole("button", { name: /Register Payment|ลงทะเบียนการชำระ|ชำระเงิน/i }).first().click();
    await page.getByText("Register Payment", { exact: false }).first().waitFor({ state: "visible", timeout: 30000 });
    await screenshot(page, "02_payment_modal_before_create");
    const modalText = await page.locator(".modal, .o_dialog").last().innerText();
    const paymentDifferenceVisible = /Payment Difference/i.test(modalText);
    const amount86 = /86\.00|86\.0|86 ฿|86\.00 ฿/.test(modalText);
    results.push({
      step: "modal_values",
      status: !paymentDifferenceVisible && amount86 ? "pass" : "fail",
      detail: { paymentDifferenceVisible, amount86, modalText },
    });

    await page.getByRole("button", { name: /Create Payment/i }).first().click();
    await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(5000);
    await screenshot(page, "03_after_create_payment");
    const body = await page.locator("body").innerText();
    const noCrash = !/Odoo Server Error|Traceback|RPC_ERROR/i.test(body);
    results.push({ step: "create_payment_click", status: noCrash ? "pass" : "fail", detail: body.slice(0, 2000) });
  } catch (error) {
    results.push({ step: "script", status: "fail", detail: error.message });
    await screenshot(page, "error").catch(() => {});
  } finally {
    await browser.close();
    fs.writeFileSync(path.join(outDir, "results.json"), JSON.stringify(results, null, 2));
    console.log(JSON.stringify(results, null, 2));
    process.exit(results.some(r => r.status === "fail") ? 1 : 0);
  }
})();
